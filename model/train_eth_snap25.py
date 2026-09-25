"""Offline ETHUSDT LightGBM trainer on book_snapshot_25 + trades.

Keeps training code under `model/` (separate from live `asq_tick`).

For ASQ restoration (60s / aqsmodel.py), prefer:
  python -m model.train_asq_align

Example:
  python -m model.train_eth_snap25 --days 1 --predict-secs 60
  python -m model.train_eth_snap25 --predict-secs 60
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.features_snap25 import (  # noqa: E402
    FEATURE_VERSION,
    SNAP_COLS,
    Y_CLIP,
    available_feature_names,
    calculate_features,
    aggregate_1s_features,
    aggregate_trades_1s,
    merge_trade_features,
    add_forward_return,
)
from model.models import get_lgbm  # noqa: E402

DATA_DIR = ROOT / "book_snapshot_25"
TRADES_DIR = DATA_DIR / "trades"
CACHE_DIR = Path(__file__).resolve().parent / "cache"
RESULT_DIR = Path(__file__).resolve().parent / "result"


def _day_paths(data_dir: Path) -> list[Path]:
    paths = sorted(data_dir.glob("book_snapshot_25_*.csv"))
    # prefer plain csv over accidental matches
    return [p for p in paths if not p.name.endswith(".zst")]


def _cache_path(day: str) -> Path:
    return CACHE_DIR / f"eth_1s_{FEATURE_VERSION}_{day}.parquet"


def _day_from_name(path: Path) -> str:
    # book_snapshot_25_2026-09-04.csv
    return path.stem.replace("book_snapshot_25_", "")


def load_day_1s(path: Path, chunksize: int = 400_000) -> pd.DataFrame:
    """Stream a multi-GB snapshot file down to ~1 row/second."""
    usecols = ["timestamp", *SNAP_COLS]
    parts: list[pd.DataFrame] = []
    t0 = time.time()
    rows_in = 0
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize):
        rows_in += len(chunk)
        chunk = chunk.dropna(subset=["timestamp"])
        chunk["sec"] = (chunk["timestamp"].astype("int64") // 1_000_000).astype("int64")
        parts.append(chunk.sort_values("timestamp").groupby("sec", as_index=False).tail(1))
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    df = df.sort_values("timestamp").groupby("sec", as_index=False).tail(1).reset_index(drop=True)
    print(
        f"  {path.name}: raw≈{rows_in:,} -> 1s={len(df):,} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    return df


def load_day_trades(day: str, trades_dir: Path = TRADES_DIR) -> pd.DataFrame | None:
    path = trades_dir / f"trades_{day}.csv"
    if not path.exists():
        print(f"  trades missing for {day} (fill zeros)", flush=True)
        return None
    t0 = time.time()
    df = pd.read_csv(path, usecols=["timestamp", "side", "price", "amount"])
    print(f"  trades_{day}.csv: rows={len(df):,} in {time.time() - t0:.1f}s", flush=True)
    return df


def build_day_bars(
    path: Path,
    predict_secs: int,
    force: bool = False,
    trades_dir: Path = TRADES_DIR,
) -> pd.DataFrame:
    day = _day_from_name(path)
    cache = _cache_path(day)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache.exists() and not force:
        print(f"  cache hit {cache.name}", flush=True)
        return pd.read_parquet(cache)

    one_s = load_day_1s(path)
    if one_s.empty:
        raise RuntimeError(f"no rows in {path}")
    feat = calculate_features(one_s)
    bars = aggregate_1s_features(feat)
    trades = load_day_trades(day, trades_dir=trades_dir)
    trades_1s = aggregate_trades_1s(trades) if trades is not None else None
    bars = merge_trade_features(bars, trades_1s)
    bars = add_forward_return(bars, predict_secs=predict_secs)
    bars["trade_date"] = day
    bars.to_parquet(cache, index=False)
    print(f"  wrote {cache} rows={len(bars):,}", flush=True)
    return bars


def train_from_bars(
    bars: pd.DataFrame,
    predict_secs: int,
    test_days: int = 2,
) -> tuple[object, dict]:
    feats = available_feature_names(bars.columns)
    data = bars.replace([np.inf, -np.inf], np.nan).dropna(subset=[*feats, "ret_fwd", "mid_price"])
    if len(data) < 1_000:
        raise RuntimeError(f"not enough clean bars to train ({len(data)})")

    dates = sorted(data["trade_date"].unique())
    # dates[-0:] is the full list in Python — treat test_days<=0 as time split.
    if test_days > 0 and len(dates) > test_days:
        test_set = set(dates[-test_days:])
        train_df = data[~data["trade_date"].isin(test_set)]
        test_df = data[data["trade_date"].isin(test_set)]
    else:
        split = int(len(data) * 0.8)
        train_df = data.iloc[:split]
        test_df = data.iloc[split:]

    X_train = train_df[feats].to_numpy(dtype=float)
    y_train = np.clip(train_df["ret_fwd"].to_numpy(dtype=float), -Y_CLIP, Y_CLIP)
    X_test = test_df[feats].to_numpy(dtype=float)
    y_test = np.clip(test_df["ret_fwd"].to_numpy(dtype=float), -Y_CLIP, Y_CLIP)

    print(
        f"train rows={len(train_df):,} days={sorted(train_df['trade_date'].unique())}\n"
        f"test  rows={len(test_df):,} days={sorted(test_df['trade_date'].unique())}\n"
        f"features={len(feats)} predict_secs={predict_secs}",
        flush=True,
    )
    model, y_pred = get_lgbm(X_train, y_train, X_test, y_test)
    corr = float(np.corrcoef(y_test, y_pred)[0, 1]) if len(y_test) > 2 else float("nan")
    print(f"oos_corr={corr:.4f}", flush=True)

    meta = {
        "symbol": "ETHUSDT",
        "predict_secs": predict_secs,
        "y_clip": Y_CLIP,
        "feature_version": FEATURE_VERSION,
        "features": feats,
        "oos_corr": corr,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "train_days": sorted(map(str, train_df["trade_date"].unique())),
        "test_days": sorted(map(str, test_df["trade_date"].unique())),
    }
    return model, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ETH snap25 LightGBM offline")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--predict-secs", type=int, default=60)
    parser.add_argument("--days", type=int, default=0, help="use only the last N days (0=all)")
    parser.add_argument("--test-days", type=int, default=2)
    parser.add_argument("--force-cache", action="store_true")
    parser.add_argument(
        "--out",
        type=Path,
        default=RESULT_DIR / "lgbm_eth_snap25.pkl",
    )
    args = parser.parse_args()

    paths = _day_paths(args.data_dir)
    if not paths:
        raise SystemExit(f"no book_snapshot_25_*.csv under {args.data_dir}")
    if args.days > 0:
        paths = paths[-args.days :]

    print(f"days={len(paths)} from {paths[0].name} .. {paths[-1].name}", flush=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    frames = [build_day_bars(p, predict_secs=args.predict_secs, force=args.force_cache) for p in paths]
    bars = pd.concat(frames, ignore_index=True)
    model, meta = train_from_bars(bars, predict_secs=args.predict_secs, test_days=args.test_days)

    joblib.dump({"model": model, "meta": meta}, args.out)
    meta_path = args.out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"saved model -> {args.out}")
    print(f"saved meta  -> {meta_path}")


if __name__ == "__main__":
    main()
