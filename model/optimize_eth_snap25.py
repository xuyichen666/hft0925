"""Professional optimization pass for ETH snap25 fair model.

Uses existing `model/cache/eth_1s_v5_*.parquet` (no re-read of multi-GB CSVs):
1) sweep forward horizons
2) walk-forward day IC
3) prune unstable / low-importance features
4) refit stronger LightGBM with early stopping
5) write production pkl + optimization report

Example:
  python -m model.optimize_eth_snap25
  python -m model.optimize_eth_snap25 --horizons 60,120,300,600,900 --top-frac 0.55
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
from model.models import get_lgbm  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / "cache"
RESULT_DIR = Path(__file__).resolve().parent / "result"


# ==============================================================================
# 数据加载
# ==============================================================================
def _load_caches(cache_glob: str = "eth_1s_v5_*.parquet") -> pd.DataFrame:
    paths = sorted(CACHE_DIR.glob(cache_glob))
    if not paths:
        raise SystemExit(f"no caches under {CACHE_DIR}/{cache_glob} — run gen_cache.py first")
    frames = []
    for p in paths:
        df = pd.read_parquet(p)
        if "trade_date" not in df.columns:
            day = p.stem.split("_")[-1]
            df["trade_date"] = day
        frames.append(df)
        print(f"  cache {p.name}: {len(df):,}", flush=True)
    out = pd.concat(frames, ignore_index=True)
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def _feature_cols(df: pd.DataFrame) -> list[str]:
    cols = set(df.columns)
    return [c for c in FEATURE_NAMES if c in cols]


# ==============================================================================
# 标签 / 工具
# ==============================================================================
def _add_label(df: pd.DataFrame, predict_secs: int) -> pd.DataFrame:
    out = df.copy()
    parts = []
    for _, g in out.groupby("trade_date", sort=True):
        g = g.sort_values("sec") if "sec" in g.columns else g
        fwd = g["mid_price"].shift(-int(predict_secs))
        g = g.copy()
        g["ret_fwd"] = fwd / g["mid_price"] - 1.0
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def _corr(y: np.ndarray, p: np.ndarray) -> float:
    if len(y) < 100 or np.std(y) < 1e-12 or np.std(p) < 1e-12:
        return float("nan")
    return float(np.corrcoef(y, p)[0, 1])


def _prep_xy(df: pd.DataFrame, feats: list[str]) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    data = df.dropna(subset=[*feats, "ret_fwd", "mid_price"]).copy()
    X = data[feats].to_numpy(dtype=float)
    y = np.clip(data["ret_fwd"].to_numpy(dtype=float), -Y_CLIP, Y_CLIP)
    return X, y, data


# ==============================================================================
# 1. Horizon sweep
# ==============================================================================
def sweep_horizons(
    bars: pd.DataFrame,
    feats: list[str],
    horizons: list[int],
    test_days: int = 2,
) -> list[dict]:
    dates = sorted(bars["trade_date"].unique())
    test_set = set(dates[-test_days:]) if len(dates) > test_days else set(dates[-1:])
    rows = []
    for h in horizons:
        labeled = _add_label(bars, h)
        if test_set:
            train_df = labeled[~labeled["trade_date"].isin(test_set)]
            test_df = labeled[labeled["trade_date"].isin(test_set)]
        else:
            n = int(len(labeled) * 0.8)
            train_df, test_df = labeled.iloc[:n], labeled.iloc[n:]

        Xtr, ytr, _ = _prep_xy(train_df, feats)
        Xte, yte, test_clean = _prep_xy(test_df, feats)

        if len(ytr) < 1000 or len(yte) < 100:
            continue

        train_dates = sorted(train_df["trade_date"].unique())
        if len(train_dates) >= 2:
            va_day = train_dates[-1]
            tr = train_df[train_df["trade_date"] != va_day]
            va = train_df[train_df["trade_date"] == va_day]
            Xa, ya, _ = _prep_xy(tr, feats)
            Xb, yb, _ = _prep_xy(va, feats)
        else:
            Xa, ya, Xb, yb = Xtr, ytr, Xtr, ytr

        model, _ = get_lgbm(
            Xa, ya, Xb, yb,
            n_estimators=400, learning_rate=0.03,
            max_depth=5, num_leaves=24,
            early_stopping_rounds=40, verbose=-1,
        )
        pred = model.predict(Xte)
        corr = _corr(yte, pred)

        clean = test_clean.copy()
        clean["pred"] = pred
        clean["y"] = yte
        daily = []
        for d, g in clean.groupby("trade_date"):
            daily.append({
                "day": str(d),
                "ic": _corr(g["y"].to_numpy(), g["pred"].to_numpy()),
                "n": int(len(g)),
            })
        mean_daily = float(np.nanmean([x["ic"] for x in daily])) if daily else float("nan")

        row = {
            "predict_secs": h,
            "oos_corr": corr,
            "mean_daily_ic": mean_daily,
            "daily": daily,
            "train_rows": int(len(ytr)),
            "test_rows": int(len(yte)),
        }
        rows.append(row)
        print(
            f"horizon={h:>4}s  oos_corr={corr:.4f}  "
            f"mean_daily_ic={mean_daily:.4f}  "
            f"train={len(ytr):,} test={len(yte):,}",
            flush=True,
        )
    return rows


# ==============================================================================
# 2. Feature selection
# ==============================================================================
def select_features(
    bars: pd.DataFrame,
    feats: list[str],
    predict_secs: int,
    test_days: int = 2,
    top_frac: float = 0.55,
    min_features: int = 25,
) -> tuple[list[str], dict]:
    labeled = _add_label(bars, predict_secs)
    dates = sorted(labeled["trade_date"].unique())
    test_set = set(dates[-test_days:]) if len(dates) > test_days else set(dates[-1:])
    train_df = labeled[~labeled["trade_date"].isin(test_set)]
    train_dates = sorted(train_df["trade_date"].unique())
    if len(train_dates) >= 2:
        val_day = train_dates[-1]
        tr = train_df[train_df["trade_date"] != val_day]
        va = train_df[train_df["trade_date"] == val_day]
        Xa, ya, _ = _prep_xy(tr, feats)
        Xb, yb, _ = _prep_xy(va, feats)
    else:
        Xa, ya, _ = _prep_xy(train_df, feats)
        Xb, yb = Xa, ya

    model, _ = get_lgbm(
        Xa, ya, Xb, yb,
        n_estimators=500, learning_rate=0.03,
        max_depth=5, num_leaves=24,
        early_stopping_rounds=50, verbose=-1,
    )
    imp = np.asarray(model.feature_importances_, dtype=float)
    order = np.argsort(-imp)
    ranked = [(feats[i], float(imp[i])) for i in order]
    keep_n = max(min_features, int(round(len(feats) * top_frac)))
    keep_n = min(keep_n, len(feats))
    selected = [feats[i] for i in order[:keep_n]]
    selected = [f for f, v in ranked[:keep_n] if v > 0] or selected
    info = {
        "ranked": [{"name": n, "importance": v} for n, v in ranked],
        "selected": selected,
        "kept": len(selected),
        "total": len(feats),
    }
    print(f"feature select: keep {len(selected)}/{len(feats)} (top_frac={top_frac})", flush=True)
    print("top15:", ", ".join(f"{n}:{int(v)}" for n, v in ranked[:15]), flush=True)
    return selected, info


# ==============================================================================
# 3. Walk-forward IC
# ==============================================================================
def walk_forward_ic(
    bars: pd.DataFrame,
    feats: list[str],
    predict_secs: int,
    min_train_days: int = 5,
) -> list[dict]:
    labeled = _add_label(bars, predict_secs)
    dates = sorted(labeled["trade_date"].unique())
    rows = []
    for i in range(min_train_days, len(dates)):
        train_days = dates[:i]
        test_day = dates[i]
        train_df = labeled[labeled["trade_date"].isin(train_days)]
        test_df = labeled[labeled["trade_date"] == test_day]
        Xtr, ytr, _ = _prep_xy(train_df, feats)
        Xte, yte, _ = _prep_xy(test_df, feats)
        if len(ytr) < 5_000 or len(yte) < 1_000:
            continue
        if len(train_days) >= 2:
            va_day = train_days[-1]
            tr = train_df[train_df["trade_date"] != va_day]
            va = train_df[train_df["trade_date"] == va_day]
            Xa, ya, _ = _prep_xy(tr, feats)
            Xb, yb, _ = _prep_xy(va, feats)
        else:
            Xa, ya, Xb, yb = Xtr, ytr, Xtr, ytr
        model, _ = get_lgbm(
            Xa, ya, Xb, yb,
            n_estimators=500, learning_rate=0.03,
            max_depth=5, num_leaves=24,
            early_stopping_rounds=50, verbose=-1,
        )
        pred = model.predict(Xte)
        ic = _corr(yte, pred)
        q = np.nanpercentile(pred, [20, 80])
        mask_hi = pred >= q[1]
        mask_lo = pred <= q[0]
        spread = float(yte[mask_hi].mean() - yte[mask_lo].mean()) if mask_hi.any() and mask_lo.any() else float("nan")
        rows.append({
            "test_day": str(test_day),
            "train_days": list(map(str, train_days)),
            "ic": ic,
            "pred_q2080_ret_spread": spread,
            "test_rows": int(len(yte)),
        })
        print(f"WF {test_day}: ic={ic:.4f} q2080_spread={spread:.6f} n={len(yte):,}", flush=True)
    return rows


# ==============================================================================
# 4. Production fit
# ==============================================================================
def fit_production(
    bars: pd.DataFrame,
    feats: list[str],
    predict_secs: int,
    test_days: int = 2,
) -> tuple[object, dict, np.ndarray, np.ndarray]:
    labeled = _add_label(bars, predict_secs)
    dates = sorted(labeled["trade_date"].unique())
    test_set = set(dates[-test_days:])
    train_df = labeled[~labeled["trade_date"].isin(test_set)]
    test_df = labeled[labeled["trade_date"].isin(test_set)]

    train_dates = sorted(train_df["trade_date"].unique())
    va_day = train_dates[-1]
    tr = train_df[train_df["trade_date"] != va_day]
    va = train_df[train_df["trade_date"] == va_day]
    Xa, ya, _ = _prep_xy(tr, feats)
    Xb, yb, _ = _prep_xy(va, feats)
    Xte, yte, test_clean = _prep_xy(test_df, feats)

    model, _ = get_lgbm(
        Xa, ya, Xb, yb,
        n_estimators=800, learning_rate=0.03,
        max_depth=6, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8,
        reg_lambda=1.0, min_child_samples=80,
        early_stopping_rounds=60, verbose=-1,
    )
    pred = model.predict(Xte)
    corr = _corr(yte, pred)
    pred_va = model.predict(Xb)
    thr = float(np.nanpercentile(np.abs(pred_va), 60))
    meta = {
        "symbol": "ETHUSDT",
        "predict_secs": predict_secs,
        "y_clip": Y_CLIP,
        "feature_version": FEATURE_VERSION,
        "features": feats,
        "oos_corr": corr,
        "signal_threshold": thr,
        "train_rows": int(len(ya) + len(yb)),
        "test_rows": int(len(yte)),
        "train_days": sorted(map(str, train_df["trade_date"].unique())),
        "valid_day": str(va_day),
        "test_days": sorted(map(str, test_df["trade_date"].unique())),
        "optimized": True,
    }
    print(f"production oos_corr={corr:.4f} signal_threshold≈{thr:.6f}", flush=True)
    return model, meta, yte, pred


# ==============================================================================
# 5. Main
# ==============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize ETH snap25 LightGBM")
    parser.add_argument("--horizons", type=str, default="60,120,300,600,900")
    parser.add_argument("--test-days", type=int, default=2)
    parser.add_argument("--top-frac", type=float, default=0.55)
    parser.add_argument("--min-features", type=int, default=25)
    parser.add_argument("--cache-glob", type=str, default="eth_1s_v5_*.parquet")
    parser.add_argument("--out", type=Path, default=RESULT_DIR / "lgbm_eth_snap25.pkl")
    parser.add_argument("--report", type=Path, default=RESULT_DIR / "optimize_report.json")
    args = parser.parse_args()

    horizons = [int(x) for x in args.horizons.split(",") if x.strip()]
    print("loading caches...", flush=True)
    bars = _load_caches(args.cache_glob)
    feats_all = _feature_cols(bars)
    print(f"bars={len(bars):,} days={sorted(bars['trade_date'].unique())} feats={len(feats_all)}", flush=True)

    print("\n=== horizon sweep ===", flush=True)
    sweep = sweep_horizons(bars, feats_all, horizons, test_days=args.test_days)
    if not sweep:
        raise SystemExit("no valid horizon result")
    best = max(sweep, key=lambda r: (
        r["mean_daily_ic"] if np.isfinite(r["mean_daily_ic"]) else -1,
        r["oos_corr"] if np.isfinite(r["oos_corr"]) else -1,
    ))
    best_h = int(best["predict_secs"])
    print(f"\nbest horizon={best_h}s (mean_daily_ic={best['mean_daily_ic']:.4f}, oos={best['oos_corr']:.4f})", flush=True)

    print("\n=== feature selection ===", flush=True)
    selected, feat_info = select_features(
        bars, feats_all,
        predict_secs=best_h,
        test_days=args.test_days,
        top_frac=args.top_frac,
        min_features=args.min_features,
    )

    print("\n=== walk-forward ===", flush=True)
    wf = walk_forward_ic(bars, selected, predict_secs=best_h, min_train_days=5)
    wf_mean = float(np.nanmean([x["ic"] for x in wf])) if wf else float("nan")
    print(f"walk-forward mean IC={wf_mean:.4f}", flush=True)

    print("\n=== production fit ===", flush=True)
    model, meta, yte, pred = fit_production(bars, selected, predict_secs=best_h, test_days=args.test_days)
    meta["walk_forward_mean_ic"] = wf_mean
    meta["horizon_sweep"] = sweep
    meta["feature_selection"] = {
        "kept": feat_info["kept"],
        "total": feat_info["total"],
        "top15": feat_info["ranked"][:15],
    }
    meta["walk_forward"] = wf

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "meta": meta}, args.out)
    args.out.with_suffix(".json").write_text(json.dumps(meta, indent=2, default=float))
    args.report.write_text(json.dumps(meta, indent=2, default=float))
    print(f"\nsaved model  -> {args.out}")
    print(f"saved report -> {args.report}")
    print(
        f"summary: horizon={best_h}s feats={len(selected)} "
        f"oos={meta['oos_corr']:.4f} wf_ic={wf_mean:.4f} thr={meta['signal_threshold']:.6f}"
    )


if __name__ == "__main__":
    main()