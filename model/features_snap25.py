"""
Snapshot-25 + trades features —— 完整修复版 v5
- 修正列名：bids[i].price → bid_p{i}
- 修正因子顺序：先 merge trades，再算依赖 trades 的因子
- 采样 50 适配
- 输出：feature_frame() → 因子 + 标签
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


# ==============================================================================
# 0. 常量
# ==============================================================================
N_LEVELS = 25
Y_CLIP = 0.0005
FEATURE_VERSION = "v5"
TRADES_SAMPLE_RATE = 50

# 列名（标准化后）
BID_PRICE_COLS = [f"bid_p{i}" for i in range(N_LEVELS)]
BID_AMOUNT_COLS = [f"bid_q{i}" for i in range(N_LEVELS)]
ASK_PRICE_COLS = [f"ask_p{i}" for i in range(N_LEVELS)]
ASK_AMOUNT_COLS = [f"ask_q{i}" for i in range(N_LEVELS)]
SNAP_COLS = BID_PRICE_COLS + BID_AMOUNT_COLS + ASK_PRICE_COLS + ASK_AMOUNT_COLS


# ==============================================================================
# 1. 因子清单
# ==============================================================================
BASE_SNAP_FEATURES = [
    "obi",
    "slope_a", "slope_b", "slope_diff",
    "slope_a_low", "slope_b_low", "slope_a_high", "slope_b_high",
    "slope_imbalance_low", "slope_imbalance_high",
    "slope_diff_low", "slope_diff_high",
]

CROSS_SECTION_EXTRAS = [
    "spread", "spread_bp",
    "microprice_dev",
    "wmid_dev_5", "wmid_dev_10",
    "l1_imb", "l2_imb",
    "depth_imb_5", "depth_imb_10", "depth_imb_25",
    "notional_imb_5", "notional_imb_10", "notional_imb_25",
    "log_depth_ratio_5", "log_depth_ratio_10", "log_depth_ratio_25",
    "bid_top_share", "ask_top_share",
    "bid_top5_share", "ask_top5_share",
    "near_far_bid", "near_far_ask", "near_far_imb",
    "gap_bid_mean", "gap_ask_mean", "gap_diff",
    "depth_bp_5", "depth_bp_10", "depth_bp_25",
    "cum_vol_bp_5", "cum_vol_bp_10",
    "level_conc_bid", "level_conc_ask",
    "slope_convex_a", "slope_convex_b", "slope_convex_diff",
    "queue_pressure",
]

ROLLING_FEATURES = [
    "obi_change_1s", "l1_imb_change_1s", "spread_change_1s",
    "mid_ret_1s", "mid_ret_5s", "mid_ret_10s", "mid_ret_30s",
    "mid_vol_10s", "mid_vol_30s",
    "obi_ma_10s", "obi_ma_30s", "obi_z_30s",
    "spread_ma_10s", "microprice_ma_10s",
    "depth_imb_5_ma_10s", "depth_imb_5_change_5s",
]

TRADE_FEATURES = [
    "trade_count", "trade_qty", "trade_notional",
    "buy_qty", "sell_qty", "buy_notional", "sell_notional",
    "signed_qty", "signed_notional",
    "net_buy_ratio", "gross_buy_ratio",
    "trade_vwap_dev", "trade_px_range", "trade_last_dev",
    "large_trade_share", "buy_count_ratio",
    "trade_qty_1s_z",
    "trade_qty_sum_10s", "trade_qty_sum_60s", "trade_qty_sum_300s",
    "signed_qty_sum_10s", "signed_qty_sum_60s", "signed_qty_sum_300s",
    "net_buy_ratio_10s", "net_buy_ratio_60s", "net_buy_ratio_300s",
    "gross_buy_ratio_60s", "trade_intensity_60s",
    "signed_qty_ma_30s", "ofi_vs_depth",
]

MEAN_FEATURES = [
    "slope_a_mean", "slope_b_mean", "slope_diff_mean",
    "slope_a_low_mean", "slope_b_low_mean",
    "slope_a_high_mean", "slope_b_high_mean",
    "slope_imbalance_low_mean", "slope_imbalance_high_mean",
    "slope_diff_low_mean", "slope_diff_high_mean",
]

MOMENT_FEATURES = [
    "RealizedSkewness", "RealizedKurtosis", "DownsideVolRatio",
    "VolumeSkewness", "VolumeKurtosis",
    "NonlinearVol", "VolumeStd",
    "MsVol", "MsDiffMean", "MsDiffStd",
]

GAP_FEATURES = [
    "OFI_1", "OFI_5", "VPIN_60",
    "sec_in_min", "is_minute_open", "is_minute_close",
]

ALL_FEATURES = (
    BASE_SNAP_FEATURES + MEAN_FEATURES
    + CROSS_SECTION_EXTRAS + ROLLING_FEATURES + TRADE_FEATURES
    + MOMENT_FEATURES + GAP_FEATURES
)
FEATURE_NAMES = list(dict.fromkeys(ALL_FEATURES))


CORE_FEATURES_1MIN = [
    "microprice_dev", "l1_imb", "depth_imb_5", "depth_imb_10", "depth_imb_25",
    "queue_pressure", "log_depth_ratio_5", "wmid_dev_5", "cum_vol_bp_5",
    "spread_bp",
    "slope_diff", "slope_imbalance_low", "slope_convex_diff",
    "mid_ret_5s", "mid_ret_30s", "obi_z_30s",
    "depth_imb_5_change_5s", "mid_vol_30s",
    "RealizedKurtosis", "RealizedSkewness",
    "NonlinearVol",
    "OFI_1",
]

CORE_FEATURES_5MIN = CORE_FEATURES_1MIN + [
    "net_buy_ratio_60s", "net_buy_ratio_300s", "gross_buy_ratio_60s",
    "trade_intensity_60s", "signed_qty_ma_30s", "ofi_vs_depth",
    "large_trade_share",
]

CORE_FEATURES = CORE_FEATURES_5MIN


# ==============================================================================
# 2. 工具函数
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


def _herfindahl(amounts):
    tot = np.nansum(amounts, axis=1, keepdims=True)
    shares = _safe_div(amounts, tot)
    return np.nansum(shares * shares, axis=1)


def _depth_weighted_mid(bid_p, ask_p, bid_a, ask_a, n):
    b_n = np.nansum(bid_p[:, :n] * bid_a[:, :n], axis=1)
    a_n = np.nansum(ask_p[:, :n] * ask_a[:, :n], axis=1)
    b_v = np.nansum(bid_a[:, :n], axis=1)
    a_v = np.nansum(ask_a[:, :n], axis=1)
    bid_vwap = _safe_div(b_n, b_v)
    ask_vwap = _safe_div(a_n, a_v)
    return 0.5 * (bid_vwap + ask_vwap)


# ==============================================================================
# 3. 盘口因子
# ==============================================================================
def calculate_features(df: pd.DataFrame, low_levels: int = 5) -> pd.DataFrame:
    out = df.copy()
    bid_p = out[BID_PRICE_COLS].to_numpy(dtype=float)
    bid_a = out[BID_AMOUNT_COLS].to_numpy(dtype=float)
    ask_p = out[ASK_PRICE_COLS].to_numpy(dtype=float)
    ask_a = out[ASK_AMOUNT_COLS].to_numpy(dtype=float)

    bid_notional = bid_p * bid_a
    ask_notional = ask_p * ask_a
    bid_sum = np.nansum(bid_notional, axis=1)
    ask_sum = np.nansum(ask_notional, axis=1)
    out["obi"] = _safe_div(bid_sum - ask_sum, bid_sum + ask_sum)

    bid_amt = np.nansum(bid_a, axis=1, keepdims=True)
    ask_amt = np.nansum(ask_a, axis=1, keepdims=True)
    bid_ratio = _safe_div(np.cumsum(bid_a, axis=1), bid_amt)
    ask_ratio = _safe_div(np.cumsum(ask_a, axis=1), ask_amt)

    ask_slope = _batch_slope(ask_ratio, ask_p)
    bid_slope = -_batch_slope(bid_ratio, bid_p)
    out["slope_a"] = ask_slope
    out["slope_b"] = bid_slope
    out["slope_diff"] = ask_slope - bid_slope

    low = slice(0, low_levels)
    high = slice(low_levels, N_LEVELS)
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

    best_bid = bid_p[:, 0]
    best_ask = ask_p[:, 0]
    best_bv = bid_a[:, 0]
    best_av = ask_a[:, 0]
    mid = (best_bid + best_ask) / 2.0
    spread = best_ask - best_bid
    out["mid_price"] = mid
    out["spread"] = spread
    out["spread_bp"] = _safe_div(spread, mid) * 1e4
    micro = _safe_div(best_ask * best_bv + best_bid * best_av, best_bv + best_av)
    out["microprice_dev"] = _safe_div(micro - mid, mid)
    out["l1_imb"] = _safe_div(best_bv - best_av, best_bv + best_av)
    out["l2_imb"] = _safe_div(
        bid_a[:, 0] + bid_a[:, 1] - ask_a[:, 0] - ask_a[:, 1],
        bid_a[:, 0] + bid_a[:, 1] + ask_a[:, 0] + ask_a[:, 1],
    )

    for n in (5, 10, 25):
        b = np.nansum(bid_a[:, :n], axis=1)
        a = np.nansum(ask_a[:, :n], axis=1)
        out[f"depth_imb_{n}"] = _safe_div(b - a, b + a)
        bn = np.nansum(bid_notional[:, :n], axis=1)
        an = np.nansum(ask_notional[:, :n], axis=1)
        out[f"notional_imb_{n}"] = _safe_div(bn - an, bn + an)
        out[f"log_depth_ratio_{n}"] = np.log(np.maximum(b, 1e-12)) - np.log(np.maximum(a, 1e-12))

    for n in (5, 10):
        wmid = _depth_weighted_mid(bid_p, ask_p, bid_a, ask_a, n)
        out[f"wmid_dev_{n}"] = _safe_div(wmid - mid, mid)

    bid_tot = np.nansum(bid_a, axis=1)
    ask_tot = np.nansum(ask_a, axis=1)
    out["bid_top_share"] = _safe_div(best_bv, bid_tot)
    out["ask_top_share"] = _safe_div(best_av, ask_tot)
    out["bid_top5_share"] = _safe_div(np.nansum(bid_a[:, :5], axis=1), bid_tot)
    out["ask_top5_share"] = _safe_div(np.nansum(ask_a[:, :5], axis=1), ask_tot)

    near_b = np.nansum(bid_a[:, :5], axis=1)
    far_b = np.nansum(bid_a[:, 5:], axis=1)
    near_a = np.nansum(ask_a[:, :5], axis=1)
    far_a = np.nansum(ask_a[:, 5:], axis=1)
    out["near_far_bid"] = _safe_div(near_b, far_b)
    out["near_far_ask"] = _safe_div(near_a, far_a)
    out["near_far_imb"] = _safe_div(near_b - near_a, far_b + far_a + 1e-12)

    bid_gaps = (bid_p[:, :-1] - bid_p[:, 1:]) / mid[:, None]
    ask_gaps = (ask_p[:, 1:] - ask_p[:, :-1]) / mid[:, None]
    out["gap_bid_mean"] = np.nanmean(bid_gaps, axis=1)
    out["gap_ask_mean"] = np.nanmean(ask_gaps, axis=1)
    out["gap_diff"] = out["gap_ask_mean"] - out["gap_bid_mean"]

    for n in (5, 10, 25):
        out[f"depth_bp_{n}"] = _safe_div(ask_p[:, n - 1] - bid_p[:, n - 1], mid) * 1e4

    bid_bp = _safe_div(mid[:, None] - bid_p, mid[:, None]) * 1e4
    ask_bp = _safe_div(ask_p - mid[:, None], mid[:, None]) * 1e4
    for thr, name in ((5.0, "cum_vol_bp_5"), (10.0, "cum_vol_bp_10")):
        b_mask = bid_bp <= thr
        a_mask = ask_bp <= thr
        out[name] = _safe_div(
            np.nansum(np.where(b_mask, bid_a, 0.0), axis=1) - np.nansum(np.where(a_mask, ask_a, 0.0), axis=1),
            np.nansum(np.where(b_mask, bid_a, 0.0), axis=1) + np.nansum(np.where(a_mask, ask_a, 0.0), axis=1),
        )

    out["level_conc_bid"] = _herfindahl(bid_a)
    out["level_conc_ask"] = _herfindahl(ask_a)
    out["queue_pressure"] = _safe_div(best_bv - best_av, bid_tot + ask_tot)
    return out


# ==============================================================================
# 4. 1 秒降采样
# ==============================================================================
def downsample_to_1s(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sec"] = (out["timestamp"].astype("int64") // 1_000_000).astype("int64")
    out = out.sort_values(["sec", "timestamp"]).groupby("sec", as_index=False).tail(1)
    return out.reset_index(drop=True)


# ==============================================================================
# 5. 滚动因子（不依赖 trades）
# ==============================================================================
def _add_rolling(out: pd.DataFrame) -> pd.DataFrame:
    mid = out["mid_price"]
    ret1 = mid.pct_change()
    out["obi_change_1s"] = out["obi"].diff()
    out["l1_imb_change_1s"] = out["l1_imb"].diff()
    out["spread_change_1s"] = out["spread"].diff()
    out["mid_ret_1s"] = ret1
    out["mid_ret_5s"] = mid.pct_change(5)
    out["mid_ret_10s"] = mid.pct_change(10)
    out["mid_ret_30s"] = mid.pct_change(30)
    out["mid_vol_10s"] = ret1.rolling(10, min_periods=5).std()
    out["mid_vol_30s"] = ret1.rolling(30, min_periods=10).std()
    out["obi_ma_10s"] = out["obi"].rolling(10, min_periods=5).mean()
    out["obi_ma_30s"] = out["obi"].rolling(30, min_periods=10).mean()
    obi_std = out["obi"].rolling(30, min_periods=10).std()
    out["obi_z_30s"] = _safe_div(
        (out["obi"] - out["obi_ma_30s"]).to_numpy(),
        obi_std.to_numpy(),
    )
    out["spread_ma_10s"] = out["spread"].rolling(10, min_periods=5).mean()
    out["microprice_ma_10s"] = out["microprice_dev"].rolling(10, min_periods=5).mean()
    out["depth_imb_5_ma_10s"] = out["depth_imb_5"].rolling(10, min_periods=5).mean()
    out["depth_imb_5_change_5s"] = out["depth_imb_5"].diff(5)

    # 高阶矩 / 波动（不依赖 trades）
    out["RealizedSkewness"] = _realized_skewness(ret1, 500)
    out["RealizedKurtosis"] = _realized_kurtosis(ret1, 500)
    out["DownsideVolRatio"] = _downside_vol_ratio(ret1, 500)
    out["NonlinearVol"] = _nonlinear_vol(ret1, 60)
    out["MsVol"] = ret1.rolling(60).std()
    out["MsDiffMean"] = mid.diff().abs().rolling(60).mean()
    out["MsDiffStd"] = mid.diff().abs().rolling(60).std()

    # 缺口（不依赖 trades）
    out["OFI_1"] = _ofi(out, levels=1)
    out["OFI_5"] = _ofi(out, levels=5)
    sec = (out["timestamp"] // 1_000_000).astype("int64") % 60
    out["sec_in_min"] = sec
    out["is_minute_open"] = (sec < 5).astype(int)
    out["is_minute_close"] = (sec > 55).astype(int)

    return out


# ==============================================================================
# 6. 高阶矩 / 波动 / 缺口 辅助函数
# ==============================================================================
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


def _ofi(bars, levels=1):
    bid = bars[[f"bid_q{i}" for i in range(levels)]].sum(axis=1) if levels > 1 else bars["bid_q0"]
    ask = bars[[f"ask_q{i}" for i in range(levels)]].sum(axis=1) if levels > 1 else bars["ask_q0"]
    bid_chg = bid.diff()
    ask_chg = ask.diff()
    bp_chg = bars["bid_p0"].diff()
    ap_chg = bars["ask_p0"].diff()
    ofi = (bid_chg.where(bp_chg >= 0, 0) - bid_chg.where(bp_chg < 0, 0)) - \
          (ask_chg.where(ap_chg <= 0, 0) - ask_chg.where(ap_chg > 0, 0))
    return ofi.fillna(0.0)


def _vpin(bars, window=60):
    buy = bars["buy_qty"]
    sell = bars["sell_qty"]
    total = (buy + sell).replace(0, np.nan)
    imb = (buy - sell).abs() / total
    return imb.rolling(window, min_periods=10).mean().fillna(0.0)


def _add_moment_and_gap(out: pd.DataFrame) -> pd.DataFrame:
    """依赖 trades 的因子，必须在 merge_trade_features 之后调用。"""
    if "trade_qty" in out.columns:
        out["VolumeSkewness"] = out["trade_qty"].rolling(60).skew()
        out["VolumeKurtosis"] = out["trade_qty"].rolling(60).kurt()
        out["VolumeStd"] = out["trade_qty"].rolling(60).std()
    else:
        out["VolumeSkewness"] = np.nan
        out["VolumeKurtosis"] = np.nan
        out["VolumeStd"] = np.nan

    if "buy_qty" in out.columns and "sell_qty" in out.columns:
        out["VPIN_60"] = _vpin(out, 60)
    else:
        out["VPIN_60"] = np.nan
    return out


# ==============================================================================
# 7. 1 秒聚合
# ==============================================================================
def aggregate_1s_features(feat: pd.DataFrame) -> pd.DataFrame:
    feat = feat.sort_values("sec")
    # ---- 新增：保留原始盘口列，供 _ofi / _vpin 用 ----
    raw_cols = []
    for i in range(N_LEVELS):
        raw_cols += [f"bid_p{i}", f"bid_q{i}", f"ask_p{i}", f"ask_q{i}"]
    last_cols = BASE_SNAP_FEATURES + CROSS_SECTION_EXTRAS + raw_cols + ["mid_price", "timestamp"]
    last_cols = [c for c in last_cols if c in feat.columns]
    g = feat.groupby("sec", sort=True)
    last = g[last_cols].last().reset_index()
    means = g[BASE_SNAP_FEATURES].mean().add_suffix("_mean")
    means = means[[c for c in MEAN_FEATURES if c in means.columns]].reset_index()
    out = last.merge(means, on="sec", how="left")
    out = _add_rolling(out)
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def aggregate_trades_1s(trades: pd.DataFrame) -> pd.DataFrame:
    if trades is None or trades.empty:
        return pd.DataFrame(columns=["sec"])

    df = trades.copy()
    df["sec"] = (df["timestamp"].astype("int64") // 1_000_000).astype("int64")
    side = df["side"].astype(str).str.lower()
    is_buy = side.eq("buy")
    is_sell = side.eq("sell")
    qty = df["amount"].astype(float)
    px = df["price"].astype(float)
    notional = px * qty
    df["buy_qty"] = np.where(is_buy, qty, 0.0)
    df["sell_qty"] = np.where(is_sell, qty, 0.0)
    df["buy_notional"] = np.where(is_buy, notional, 0.0)
    df["sell_notional"] = np.where(is_sell, notional, 0.0)
    df["signed_qty"] = np.where(is_buy, qty, -qty)
    df["signed_notional"] = np.where(is_buy, notional, -notional)
    df["notional"] = notional
    df["qty"] = qty
    df["is_buy"] = is_buy.astype(np.int8)
    med = float(np.nanmedian(notional)) if len(notional) else 0.0
    df["large_notional"] = np.where(notional >= max(med, 1e-12), notional, 0.0)

    g = df.groupby("sec", sort=True)
    out = pd.DataFrame({
        "trade_count": g.size(),
        "trade_qty": g["qty"].sum(),
        "trade_notional": g["notional"].sum(),
        "buy_qty": g["buy_qty"].sum(),
        "sell_qty": g["sell_qty"].sum(),
        "buy_notional": g["buy_notional"].sum(),
        "sell_notional": g["sell_notional"].sum(),
        "signed_qty": g["signed_qty"].sum(),
        "signed_notional": g["signed_notional"].sum(),
        "trade_vwap": g["notional"].sum() / g["qty"].sum().replace(0, np.nan),
        "trade_px_max": g["price"].max(),
        "trade_px_min": g["price"].min(),
        "trade_px_last": g["price"].last(),
        "buy_count": g["is_buy"].sum(),
        "large_trade_notional": g["large_notional"].sum(),
    })
    out = out.reset_index()
    out["gross_buy_ratio"] = _safe_div(out["buy_qty"].to_numpy(), out["trade_qty"].to_numpy())
    out["net_buy_ratio"] = _safe_div(out["signed_qty"].to_numpy(), out["trade_qty"].to_numpy())
    out["trade_px_range"] = out["trade_px_max"] - out["trade_px_min"]
    out["large_trade_share"] = _safe_div(out["large_trade_notional"].to_numpy(), out["trade_notional"].to_numpy())
    out["buy_count_ratio"] = _safe_div(out["buy_count"].to_numpy(), out["trade_count"].to_numpy())
    return out


def merge_trade_features(bars: pd.DataFrame, trades_1s: pd.DataFrame | None) -> pd.DataFrame:
    out = bars.copy()
    fill0 = [
        "trade_count", "trade_qty", "trade_notional",
        "buy_qty", "sell_qty", "buy_notional", "sell_notional",
        "signed_qty", "signed_notional",
    ]
    if trades_1s is None or trades_1s.empty:
        for c in fill0:
            out[c] = 0.0
        out["gross_buy_ratio"] = 0.5
        out["net_buy_ratio"] = 0.0
        out["trade_vwap"] = np.nan
        out["trade_px_range"] = 0.0
        out["trade_px_last"] = np.nan
        out["large_trade_share"] = 0.0
        out["buy_count_ratio"] = 0.5
    else:
        keep = ["sec", *fill0, "gross_buy_ratio", "net_buy_ratio",
                "trade_vwap", "trade_px_range", "trade_px_last",
                "large_trade_share", "buy_count_ratio"]
        keep = [c for c in keep if c in trades_1s.columns]
        out = out.merge(trades_1s[keep], on="sec", how="left")
        for c in fill0:
            if c in out.columns:
                out[c] = out[c].fillna(0.0)
        out["gross_buy_ratio"] = out["gross_buy_ratio"].fillna(0.5)
        out["net_buy_ratio"] = out["net_buy_ratio"].fillna(0.0)
        out["trade_px_range"] = out["trade_px_range"].fillna(0.0)
        out["large_trade_share"] = out["large_trade_share"].fillna(0.0)
        out["buy_count_ratio"] = out["buy_count_ratio"].fillna(0.5)

    mid = out["mid_price"].to_numpy(dtype=float)
    vwap = out["trade_vwap"].to_numpy(dtype=float)
    last_px = out["trade_px_last"].to_numpy(dtype=float)
    out["trade_vwap_dev"] = np.where(np.isfinite(vwap), _safe_div(vwap - mid, mid), 0.0)
    out["trade_last_dev"] = np.where(np.isfinite(last_px), _safe_div(last_px - mid, mid), 0.0)

    qty = out["trade_qty"]
    qty_ma = qty.rolling(60, min_periods=10).mean()
    qty_sd = qty.rolling(60, min_periods=10).std()
    out["trade_qty_1s_z"] = _safe_div((qty - qty_ma).to_numpy(), qty_sd.to_numpy())

    for w, name in ((10, "trade_qty_sum_10s"), (60, "trade_qty_sum_60s"), (300, "trade_qty_sum_300s")):
        out[name] = qty.rolling(w, min_periods=max(1, w // 5)).sum()
    for w, name in ((10, "signed_qty_sum_10s"), (60, "signed_qty_sum_60s"), (300, "signed_qty_sum_300s")):
        out[name] = out["signed_qty"].rolling(w, min_periods=max(1, w // 5)).sum()

    buy60 = out["buy_qty"].rolling(60, min_periods=10).sum()
    sell60 = out["sell_qty"].rolling(60, min_periods=10).sum()
    tot10 = out["trade_qty_sum_10s"]
    tot60 = out["trade_qty_sum_60s"]
    tot300 = out["trade_qty_sum_300s"]
    out["net_buy_ratio_10s"] = _safe_div(out["signed_qty_sum_10s"].to_numpy(), tot10.to_numpy())
    out["net_buy_ratio_60s"] = _safe_div(out["signed_qty_sum_60s"].to_numpy(), tot60.to_numpy())
    out["net_buy_ratio_300s"] = _safe_div(out["signed_qty_sum_300s"].to_numpy(), tot300.to_numpy())
    out["gross_buy_ratio_60s"] = _safe_div(buy60.to_numpy(), (buy60 + sell60).to_numpy())
    out["trade_intensity_60s"] = out["trade_count"].rolling(60, min_periods=10).sum()
    out["signed_qty_ma_30s"] = out["signed_qty"].rolling(30, min_periods=10).mean()

    out["ofi_vs_depth"] = _safe_div(
        out["signed_qty"].to_numpy(dtype=float),
        (qty_ma.fillna(0.0) + 1e-8).to_numpy(dtype=float),
    )

    trade_fill = {
        "trade_qty_1s_z": 0.0,
        "net_buy_ratio_10s": 0.0, "net_buy_ratio_60s": 0.0, "net_buy_ratio_300s": 0.0,
        "gross_buy_ratio_60s": 0.5,
        "trade_intensity_60s": 0.0,
        "signed_qty_ma_30s": 0.0,
        "ofi_vs_depth": 0.0,
        "trade_qty_sum_10s": 0.0, "trade_qty_sum_60s": 0.0, "trade_qty_sum_300s": 0.0,
        "signed_qty_sum_10s": 0.0, "signed_qty_sum_60s": 0.0, "signed_qty_sum_300s": 0.0,
    }
    for col, val in trade_fill.items():
        if col in out.columns:
            out[col] = out[col].fillna(val)

    out = out.replace([np.inf, -np.inf], np.nan)
    return out


# ==============================================================================
# 8. 标签
# ==============================================================================
def add_forward_return(bars: pd.DataFrame, predict_secs: int) -> pd.DataFrame:
    out = bars.copy()
    fwd = out["mid_price"].shift(-int(predict_secs))
    out["ret_fwd"] = fwd / out["mid_price"] - 1.0
    return out


# ==============================================================================
# 9. 主流程
# ==============================================================================
def feature_frame(
    snap: pd.DataFrame,
    predict_secs: int = 60,
    trades: pd.DataFrame | None = None,
) -> pd.DataFrame:
    # ---- 列名标准化 ----
    rename_map = {}
    for i in range(N_LEVELS):
        rename_map[f'bids[{i}].price'] = f'bid_p{i}'
        rename_map[f'bids[{i}].amount'] = f'bid_q{i}'
        rename_map[f'asks[{i}].price'] = f'ask_p{i}'
        rename_map[f'asks[{i}].amount'] = f'ask_q{i}'
    snap = snap.rename(columns=rename_map)

    need = ["timestamp", *SNAP_COLS]
    missing = [c for c in need if c not in snap.columns]
    if missing:
        raise ValueError(f"snapshot missing columns: {missing[:8]}...")

    # 1. 降采样到 1 秒
    one_s = downsample_to_1s(snap[need])

    # 2. 盘口因子
    feat = calculate_features(one_s)

    # 3. 1 秒聚合 + 滚动因子（不含 trades 依赖）
    bars = aggregate_1s_features(feat)

    # 4. merge 交易因子
    trades_1s = aggregate_trades_1s(trades) if trades is not None else None
    bars = merge_trade_features(bars, trades_1s)

    # 5. 高阶矩 / 波动 / 缺口（依赖 trades）
    bars = _add_moment_and_gap(bars)

    # 6. 标签
    bars = add_forward_return(bars, predict_secs=predict_secs)
    return bars


def available_feature_names(columns: Iterable[str]) -> list[str]:
    cols = set(columns)
    return [name for name in FEATURE_NAMES if name in cols]