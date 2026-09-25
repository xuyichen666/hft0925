"""Fair mid using 25-level snapshot + trades features.

Replaces the original TOB-only fair model with the trained
`model/result/lgbm_eth_snap25.pkl` (65 features, 1-minute horizon).

Live actor passes:
- `frame`: TOB + trades 1-second bars (from `bars_to_frame`)
- `snap_frame`: optional 25-level snapshot rows (from `ASParamActor._snapshots_to_frame`)

When `snap_frame` is provided, 25-level factors are computed from it.
Missing columns are filled with 0 so the model can still run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

_MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "result" / "lgbm_eth_snap25.pkl"
_MODEL_JSON = _MODEL_PATH.with_suffix(".json")

DEFAULT_HORIZON = 60
Y_CLIP = 0.0005
N_LEVELS = 25


# ==============================================================================
# 模型加载
# ==============================================================================
def _load_trained_model():
    if not _MODEL_PATH.is_file():
        raise FileNotFoundError(f"Trained model not found: {_MODEL_PATH}")
    data = joblib.load(_MODEL_PATH)
    model = data["model"]
    meta = data.get("meta", {})
    return model, meta


def _load_feature_names() -> list[str]:
    if _MODEL_JSON.is_file():
        meta = json.loads(_MODEL_JSON.read_text())
        feats = meta.get("features", [])
        if feats:
            return list(feats)
    _, meta = _load_trained_model()
    return list(meta.get("features", []))


_MODEL, _META = _load_trained_model()
FEATURE_NAMES: list[str] = _load_feature_names()
SIGNAL_THRESHOLD: float = float(_META.get("signal_threshold", 0.0))
PREDICT_SECS: int = int(_META.get("predict_secs", DEFAULT_HORIZON))


# ==============================================================================
# 工具
# ==============================================================================
def _safe_div(num, den):
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(num, den)
    bad = (~np.isfinite(den)) | (np.abs(den) <= 1e-12)
    bad = np.broadcast_to(bad, np.broadcast_shapes(num.shape, den.shape))
    out = np.where(bad, np.nan, out)
    return out


def _realized_skewness(returns, window=500):
    ro = returns.rolling(window=window, min_periods=20)
    mean = ro.mean()
    std = ro.std().replace(0, np.nan)
    m3 = ((returns - mean) ** 3).rolling(window=window, min_periods=20).mean()
    return (m3 / (std ** 3)).fillna(0.0)


def _realized_kurtosis(returns, window=500):
    ro = returns.rolling(window=window, min_periods=20)
    mean = ro.mean()
    std = ro.std().replace(0, np.nan)
    m4 = ((returns - mean) ** 4).rolling(window=window, min_periods=20).mean()
    return (m4 / (std ** 4)).fillna(0.0)


def _downside_vol_ratio(returns, window=500, eps=1e-10):
    r_down_sq = np.where(returns < 0, returns ** 2, 0.0)
    r_total_sq = returns ** 2
    down_rv = pd.Series(r_down_sq, index=returns.index).rolling(window=window, min_periods=10).sum()
    total_rv = pd.Series(r_total_sq, index=returns.index).rolling(window=window, min_periods=10).sum()
    return (down_rv / (total_rv + eps)).fillna(0.5)


def _nonlinear_vol(returns, window=60):
    vol = returns.rolling(window).std()
    mx = vol.rolling(window).max().replace(0, np.nan)
    return np.exp(vol / mx)


def _batch_slope(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_mean = np.nanmean(x, axis=1, keepdims=True)
    y_mean = np.nanmean(y, axis=1, keepdims=True)
    xd = x - x_mean
    yd = y - y_mean
    var = np.nansum(xd * xd, axis=1)
    cov = np.nansum(xd * yd, axis=1)
    return _safe_div(cov, var)


# ==============================================================================
# 1 秒 bar → DataFrame
# ==============================================================================
def bars_to_frame(
    bid: np.ndarray,
    ask: np.ndarray,
    bid_size: np.ndarray,
    ask_size: np.ndarray,
    min_bid: np.ndarray,
    max_ask: np.ndarray,
    taker_buy_quantity: np.ndarray | None = None,
    taker_sell_quantity: np.ndarray | None = None,
    taker_buy_volume: np.ndarray | None = None,
    taker_sell_volume: np.ndarray | None = None,
) -> pd.DataFrame:
    n = len(bid)
    zeros = np.zeros(n, dtype=float)
    return pd.DataFrame(
        {
            "bid": np.asarray(bid, dtype=float),
            "ask": np.asarray(ask, dtype=float),
            "bid_size": np.asarray(bid_size, dtype=float),
            "ask_size": np.asarray(ask_size, dtype=float),
            "min_bid": np.asarray(min_bid, dtype=float),
            "max_ask": np.asarray(max_ask, dtype=float),
            "taker_buy_quantity": np.asarray(
                taker_buy_quantity if taker_buy_quantity is not None else zeros, dtype=float
            ),
            "taker_sell_quantity": np.asarray(
                taker_sell_quantity if taker_sell_quantity is not None else zeros, dtype=float
            ),
            "taker_buy_volume": np.asarray(
                taker_buy_volume if taker_buy_volume is not None else zeros, dtype=float
            ),
            "taker_sell_volume": np.asarray(
                taker_sell_volume if taker_sell_volume is not None else zeros, dtype=float
            ),
        }
    )


# ==============================================================================
# 25 档因子
# ==============================================================================
def _add_25level_features(out: pd.DataFrame, snap_frame: pd.DataFrame) -> pd.DataFrame:
    """从 25 档快照算因子。"""
    if snap_frame is None or snap_frame.empty:
        return out

    sf = snap_frame.copy()
    # 补齐列
    for i in range(N_LEVELS):
        for prefix in ["bid_p", "bid_q", "ask_p", "ask_q"]:
            c = f"{prefix}{i}"
            if c not in sf.columns:
                sf[c] = np.nan

    bid_p = sf[[f"bid_p{i}" for i in range(N_LEVELS)]].to_numpy(dtype=float)
    bid_q = sf[[f"bid_q{i}" for i in range(N_LEVELS)]].to_numpy(dtype=float)
    ask_p = sf[[f"ask_p{i}" for i in range(N_LEVELS)]].to_numpy(dtype=float)
    ask_q = sf[[f"ask_q{i}" for i in range(N_LEVELS)]].to_numpy(dtype=float)

    # 对齐长度
    n = min(len(out), len(sf))
    out = out.iloc[:n].copy()
    bid_p = bid_p[:n]
    bid_q = bid_q[:n]
    ask_p = ask_p[:n]
    ask_q = ask_q[:n]

    bid_notional = bid_p * bid_q
    ask_notional = ask_p * ask_q
    bid_sum = np.nansum(bid_notional, axis=1)
    ask_sum = np.nansum(ask_notional, axis=1)
    out["obi"] = _safe_div(bid_sum - ask_sum, bid_sum + ask_sum)

    # depth imbalance
    for lv in (5, 10, 25):
        b = np.nansum(bid_q[:, :lv], axis=1)
        a = np.nansum(ask_q[:, :lv], axis=1)
        out[f"depth_imb_{lv}"] = _safe_div(b - a, b + a)
        bn = np.nansum(bid_notional[:, :lv], axis=1)
        an = np.nansum(ask_notional[:, :lv], axis=1)
        out[f"notional_imb_{lv}"] = _safe_div(bn - an, bn + an)
        out[f"log_depth_ratio_{lv}"] = np.log(np.maximum(b, 1e-12)) - np.log(np.maximum(a, 1e-12))
        out[f"depth_bp_{lv}"] = _safe_div(ask_p[:, lv - 1] - bid_p[:, lv - 1], out["mid_price"].to_numpy()) * 1e4

    # l2_imb
    out["l2_imb"] = _safe_div(
        bid_q[:, 0] + bid_q[:, 1] - ask_q[:, 0] - ask_q[:, 1],
        bid_q[:, 0] + bid_q[:, 1] + ask_q[:, 0] + ask_q[:, 1],
    )

    # bid/ask top share
    bid_tot = np.nansum(bid_q, axis=1)
    ask_tot = np.nansum(ask_q, axis=1)
    out["bid_top_share"] = _safe_div(bid_q[:, 0], bid_tot)
    out["ask_top_share"] = _safe_div(ask_q[:, 0], ask_tot)
    out["bid_top5_share"] = _safe_div(np.nansum(bid_q[:, :5], axis=1), bid_tot)
    out["ask_top5_share"] = _safe_div(np.nansum(ask_q[:, :5], axis=1), ask_tot)

    # level concentration
    def _hhi(amounts):
        tot = np.nansum(amounts, axis=1, keepdims=True)
        shares = _safe_div(amounts, tot)
        return np.nansum(shares * shares, axis=1)
    out["level_conc_bid"] = _hhi(bid_q)
    out["level_conc_ask"] = _hhi(ask_q)

    # queue pressure
    out["queue_pressure"] = _safe_div(bid_q[:, 0] - ask_q[:, 0], bid_tot + ask_tot)

    # gap
    mid = out["mid_price"].to_numpy()
    bid_gaps = (bid_p[:, :-1] - bid_p[:, 1:]) / mid[:, None]
    ask_gaps = (ask_p[:, 1:] - ask_p[:, :-1]) / mid[:, None]
    out["gap_bid_mean"] = np.nanmean(bid_gaps, axis=1)
    out["gap_ask_mean"] = np.nanmean(ask_gaps, axis=1)
    out["gap_diff"] = out["gap_ask_mean"] - out["gap_bid_mean"]

    # slope
    bid_amt = np.nansum(bid_q, axis=1, keepdims=True)
    ask_amt = np.nansum(ask_q, axis=1, keepdims=True)
    bid_ratio = _safe_div(np.cumsum(bid_q, axis=1), bid_amt)
    ask_ratio = _safe_div(np.cumsum(ask_q, axis=1), ask_amt)

    ask_slope = _batch_slope(ask_ratio, ask_p)
    bid_slope = -_batch_slope(bid_ratio, bid_p)
    out["slope_a"] = ask_slope
    out["slope_b"] = bid_slope
    out["slope_diff"] = ask_slope - bid_slope

    low = slice(0, 5)
    high = slice(5, N_LEVELS)
    ask_low = _batch_slope(ask_ratio[:, low], ask_p[:, low])
    ask_high = _batch_slope(ask_ratio[:, high], ask_p[:, high])
    bid_low = -_batch_slope(bid_ratio[:, low], bid_p[:, low])
    bid_high = -_batch_slope(bid_ratio[:, high], bid_p[:, high])
    out["slope_a_low"] = ask_low
    out["slope_b_low"] = bid_low
    out["slope_a_high"] = ask_high
    out["slope_b_high"] = bid_high
    out["slope_imbalance_low"] = _safe_div(ask_low - bid_low, ask_low + bid_low)
    out["slope_imbalance_high"] = _safe_div(ask_high - bid_high, ask_high + bid_high)
    out["slope_diff_low"] = ask_low - bid_low
    out["slope_diff_high"] = ask_high - bid_high

    out["slope_convex_a"] = ask_high - ask_low
    out["slope_convex_b"] = bid_high - bid_low
    out["slope_convex_diff"] = out["slope_convex_a"] - out["slope_convex_b"]

    # microprice from 25 levels
    micro_25 = _safe_div(
        np.nansum(bid_p[:, :5] * bid_q[:, :5], axis=1) + np.nansum(ask_p[:, :5] * ask_q[:, :5], axis=1),
        np.nansum(bid_q[:, :5], axis=1) + np.nansum(ask_q[:, :5], axis=1),
    )
    out["wmid_dev_5"] = _safe_div(micro_25 - mid, mid)

    return out


# ==============================================================================
# TOB 因子（没有 25 档时用）
# ==============================================================================
def _add_tob_features(out: pd.DataFrame) -> pd.DataFrame:
    mid = (out["bid"] + out["ask"]) / 2.0
    out["mid_price"] = mid
    out["spread"] = out["ask"] - out["bid"]
    out["spread_bp"] = out["spread"] / mid.replace(0.0, np.nan) * 1e4

    bv = out["bid_size"]
    av = out["ask_size"]
    denom = (bv + av).replace(0.0, np.nan)
    out["l1_imb"] = (bv - av) / denom
    out["microprice_dev"] = (out["ask"] * bv + out["bid"] * av) / denom
    out["microprice_dev"] = (out["microprice_dev"] - mid) / mid.replace(0.0, np.nan)

    ret1 = mid.pct_change()
    out["mid_ret_10s"] = mid.pct_change(10)
    out["mid_ret_30s"] = mid.pct_change(30)
    out["mid_vol_10s"] = ret1.rolling(10, min_periods=5).std()
    out["mid_vol_30s"] = ret1.rolling(30, min_periods=10).std()
    out["obi"] = out["l1_imb"]
    obi_std = out["obi"].rolling(30, min_periods=10).std()
    out["obi_z_30s"] = (out["obi"] - out["obi"].rolling(30, min_periods=10).mean()) / obi_std.replace(0.0, np.nan)

    out["RealizedKurtosis"] = _realized_kurtosis(ret1, 500)
    out["RealizedSkewness"] = _realized_skewness(ret1, 500)
    out["DownsideVolRatio"] = _downside_vol_ratio(ret1, 500)
    out["NonlinearVol"] = _nonlinear_vol(ret1, 60)
    out["MsVol"] = ret1.rolling(60).std()
    out["MsDiffMean"] = mid.diff().abs().rolling(60).mean()
    out["MsDiffStd"] = mid.diff().abs().rolling(60).std()

    return out


# ==============================================================================
# 交易类因子
# ==============================================================================
def _add_trade_features(out: pd.DataFrame) -> pd.DataFrame:
    buy_vol = out["taker_buy_volume"]
    sell_vol = out["taker_sell_volume"]
    trade_vol = buy_vol + sell_vol

    qty = out.get("taker_buy_quantity", pd.Series(0.0, index=out.index)) + out.get(
        "taker_sell_quantity", pd.Series(0.0, index=out.index)
    )
    out["trade_intensity_60s"] = qty.rolling(60, min_periods=10).sum()
    out["VolumeStd"] = trade_vol.rolling(60).std()
    out["VolumeSkewness"] = trade_vol.rolling(60).skew()
    out["VolumeKurtosis"] = trade_vol.rolling(60).kurt()

    buy60 = buy_vol.rolling(60, min_periods=10).sum()
    sell60 = sell_vol.rolling(60, min_periods=10).sum()
    out["gross_buy_ratio_60s"] = buy60 / (buy60 + sell60).replace(0.0, np.nan)
    out["net_buy_ratio_60s"] = (buy60 - sell60) / (buy60 + sell60).replace(0.0, np.nan)

    buy300 = buy_vol.rolling(300, min_periods=20).sum()
    sell300 = sell_vol.rolling(300, min_periods=20).sum()
    out["net_buy_ratio_300s"] = (buy300 - sell300) / (buy300 + sell300).replace(0.0, np.nan)

    net = buy_vol - sell_vol
    out["signed_qty_sum_10s"] = net.rolling(10, min_periods=2).sum()
    out["signed_qty_sum_60s"] = net.rolling(60, min_periods=10).sum()
    out["signed_qty_sum_300s"] = net.rolling(300, min_periods=20).sum()
    out["trade_qty_sum_10s"] = trade_vol.rolling(10, min_periods=2).sum()
    out["trade_qty_sum_60s"] = trade_vol.rolling(60, min_periods=10).sum()
    out["trade_qty_sum_300s"] = trade_vol.rolling(300, min_periods=20).sum()
    out["signed_qty_ma_30s"] = net.rolling(30, min_periods=10).mean()

    qty_ma = trade_vol.rolling(60, min_periods=10).mean()
    qty_sd = trade_vol.rolling(60, min_periods=10).std()
    out["trade_qty_1s_z"] = _safe_div((trade_vol - qty_ma).to_numpy(), qty_sd.to_numpy())
    out["ofi_vs_depth"] = _safe_div(net.to_numpy(), (qty_ma.fillna(0.0) + 1e-8).to_numpy())
    out["VPIN_60"] = (net.abs() / trade_vol.replace(0.0, np.nan)).rolling(60, min_periods=10).mean().fillna(0.0)

    return out


# ==============================================================================
# 主构建
# ==============================================================================
def _build_feature_frame(
    frame: pd.DataFrame,
    snap_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """从 TOB + trades + 25 档构造特征。"""
    out = frame.copy()
    mid = (out["bid"] + out["ask"]) / 2.0
    out["mid_price"] = mid

    # 25 档因子（如果有）
    if snap_frame is not None and not snap_frame.empty:
        out = _add_25level_features(out, snap_frame)
    else:
        out = _add_tob_features(out)

    # 交易类
    out = _add_trade_features(out)

    # 缺口
    out["OFI_1"] = out.get("l1_imb", pd.Series(0.0, index=out.index)).diff().fillna(0.0)
    out["OFI_5"] = out["OFI_1"]
    out["sec_in_min"] = 0
    out["is_minute_open"] = 0
    out["is_minute_close"] = 0

    # 缺失的因子填 0
    for f in FEATURE_NAMES:
        if f not in out.columns:
            out[f] = 0.0

    out = out.replace([np.inf, -np.inf], np.nan)
    return out


# ==============================================================================
# 对外接口
# ==============================================================================
def fit_fair_model(
    frame: pd.DataFrame,
    snap_frame: pd.DataFrame | None = None,
    horizon_bars: int = DEFAULT_HORIZON,
) -> tuple[Any, float, float]:
    """加载训练好的模型，不重新 fit。"""
    if len(frame) < 60:
        raise ValueError(f"not enough bars ({len(frame)})")

    feat = _build_feature_frame(frame, snap_frame)
    row = feat[FEATURE_NAMES].iloc[[-1]].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    pred = float(_MODEL.predict(row)[0])
    if not np.isfinite(pred):
        pred = 0.0
    pred = float(np.clip(pred, -Y_CLIP, Y_CLIP))
    if abs(pred) < SIGNAL_THRESHOLD:
        pred = 0.0

    corr = float(_META.get("oos_corr", float("nan")))
    return _MODEL, corr, pred


def predict_ret(
    model: Any,
    frame: pd.DataFrame,
    snap_frame: pd.DataFrame | None = None,
    horizon_bars: int = DEFAULT_HORIZON,
) -> float:
    feat = _build_feature_frame(frame, snap_frame)
    row = feat[FEATURE_NAMES].iloc[[-1]].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    pred = float(model.predict(row)[0])
    if not np.isfinite(pred):
        return 0.0
    pred = float(np.clip(pred, -Y_CLIP, Y_CLIP))
    if abs(pred) < SIGNAL_THRESHOLD:
        pred = 0.0
    return pred


def fair_mid(mid: float, pred_ret: float) -> float:
    return float(mid) * (1.0 + float(pred_ret))