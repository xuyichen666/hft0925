"""Train ETH snap25 fair model aligned with `asq/aqsmodel.py`.

采样 50 适配：默认预测期 300 秒（5 分钟），可用 --predict-secs 改

  python -m model.train_asq_align
  python -m model.train_asq_align --predict-secs 300
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.features_snap25 import FEATURE_NAMES, FEATURE_VERSION, Y_CLIP  # noqa: E402
from model.models import get_lgbm_asq  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / "cache"
RESULT_DIR = Path(__file__).resolve().parent / "result"

# 采样 50 适配：默认 300 秒
DEFAULT_PREDICT_SECS = 60
ASQ_Y_CLIP = 0.0005


def _load_caches(cache_glob: str) -> pd.DataFrame:
    paths = sorted(CACHE_DIR.glob(cache_glob))
    if not paths:
        raise SystemExit(f"no caches {CACHE_DIR}/{cache_glob}")
    frames = []
    for p in paths:
        df = pd.read_parquet(p)
        if "trade_date" not in df.columns:
            df["trade_date"] = p.stem.split("_")[-1]
        frames.append(df)
        print(f"  {p.name}: {len(df):,}", flush=True)
    return pd.concat(frames, ignore_index=True).replace([np.inf, -np.inf], np.nan)


def _feature_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_NAMES if c in df.columns]


def _label(df: pd.DataFrame, predict_secs: int) -> pd.DataFrame:
    parts = []
    for _, g in df.groupby("trade_date", sort=True):
        g = g.sort_values("sec") if "sec" in g.columns else g.copy()
        g = g.copy()
        g["ret_fwd"] = g["mid_price"].shift(-int(predict_secs)) / g["mid_price"] - 1.0
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="ASQ-aligned ETH snap25 train")
    parser.add_argument("--cache-glob", default="eth_1s_v5_*.parquet")
    parser.add_argument("--test-days", type=int, default=2)
    parser.add_argument("--predict-secs", type=int, default=DEFAULT_PREDICT_SECS)
    parser.add_argument("--out", type=Path, default=RESULT_DIR / "lgbm_eth_snap25.pkl")
    args = parser.parse_args()

    print(f"ASQ align: predict_secs={args.predict_secs}, clip=±5bp", flush=True)
    bars = _load_caches(args.cache_glob)
    feats = _feature_cols(bars)
    labeled = _label(bars, args.predict_secs)

    dates = sorted(labeled["trade_date"].unique())
    test_set = set(dates[-args.test_days:]) if len(dates) > args.test_days else set()
    if test_set:
        train_df = labeled[~labeled["trade_date"].isin(test_set)]
        test_df = labeled[labeled["trade_date"].isin(test_set)]
    else:
        n = int(len(labeled) * 0.8)
        train_df, test_df = labeled.iloc[:n], labeled.iloc[n:]

    need = [*feats, "ret_fwd", "mid_price"]
    train_df = train_df.dropna(subset=need)
    test_df = test_df.dropna(subset=need)

    Xtr = train_df[feats].to_numpy(dtype=float)
    ytr = np.clip(train_df["ret_fwd"].to_numpy(dtype=float), -ASQ_Y_CLIP, ASQ_Y_CLIP)
    Xte = test_df[feats].to_numpy(dtype=float)
    yte = np.clip(test_df["ret_fwd"].to_numpy(dtype=float), -ASQ_Y_CLIP, ASQ_Y_CLIP)

    print(
        f"feats={len(feats)} train={len(ytr):,} days={sorted(train_df['trade_date'].unique())}\n"
        f"test={len(yte):,} days={sorted(test_df['trade_date'].unique())}",
        flush=True,
    )
    model, pred = get_lgbm_asq(Xtr, ytr, Xte, yte)
    corr = float(np.corrcoef(yte, pred)[0, 1]) if len(yte) > 2 else float("nan")
    print(f"oos_corr={corr:.4f}", flush=True)

    tmp = test_df.copy()
    tmp["pred"] = pred
    tmp["y"] = yte
    daily = []
    for d, g in tmp.groupby("trade_date"):
        ic = float(np.corrcoef(g["y"], g["pred"])[0, 1]) if len(g) > 100 else float("nan")
        daily.append({"day": str(d), "ic": ic, "n": int(len(g))})
        print(f"  day {d}: ic={ic:.4f} n={len(g):,}", flush=True)

    meta = {
        "symbol": "ETHUSDT",
        "predict_secs": args.predict_secs,
        "y_clip": ASQ_Y_CLIP,
        "feature_version": FEATURE_VERSION,
        "features": feats,
        "oos_corr": corr,
        "signal_threshold": 0.0,
        "aligned_with": "asq/aqsmodel.py",
        "lgbm": "asq/models.py",
        "fair_formula": "mid * (1 + pred)",
        "train_rows": int(len(ytr)),
        "test_rows": int(len(yte)),
        "train_days": sorted(map(str, train_df["trade_date"].unique())),
        "test_days": sorted(map(str, test_df["trade_date"].unique())),
        "daily_ic": daily,
        "optimized": False,
        "asq_align": True,
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "meta": meta}, args.out)
    args.out.with_suffix(".json").write_text(json.dumps(meta, indent=2, default=float))
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()