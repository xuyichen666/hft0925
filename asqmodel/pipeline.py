# J:\l2data\asq\pipeline.py
# 一条龙：CSV -> Parquet -> 1秒bar -> 因子(55个) -> IC -> 相关性 -> 组合
# 用法：python pipeline.py

import os
import sys
import time
import numpy as np
import pandas as pd
import polars as pl
from pathlib import Path
from scipy.stats import spearmanr

# ==================== 配置 ====================
DATA = Path(r"J:\l2data")
OUT_PARQUET = DATA / "parquet"
OUT_FACTORS = DATA / "factors"
DATES = ["2026-09-04"]     # 只跑 1 天
TARGET_HORIZON = 60        # 未来 60 秒
FEE_RATE = 2e-4            # maker 2 bps

OUT_PARQUET.mkdir(exist_ok=True)
OUT_FACTORS.mkdir(exist_ok=True)


# ==================== 波动率 ====================
def add_volatility_factors(df: pl.DataFrame) -> pl.DataFrame:
    r = pl.col("ret")
    df = df.with_columns([
        (r ** 2).rolling_sum(60).sqrt().alias("realized_volatility_60"),
        (r ** 2).rolling_sum(300).sqrt().alias("realized_volatility_300"),
        ((r ** 3).rolling_mean(60) / (r.rolling_std(60) ** 3 + 1e-9)).alias("realized_skewness_60"),
        ((r ** 4).rolling_mean(60) / (r.rolling_std(60) ** 4 + 1e-9)).alias("realized_kurtosis_60"),
        (pl.when(r > 0).then(r ** 2).otherwise(0).rolling_sum(60).sqrt()).alias("upside_volatility_60"),
        (pl.when(r < 0).then(r ** 2).otherwise(0).rolling_sum(60).sqrt()).alias("downside_volatility_60"),
    ])
    df = df.with_columns([
        (pl.col("realized_volatility_60") / (pl.col("realized_volatility_300") + 1e-9)).alias("rv_ratio"),
        (pl.col("downside_volatility_60") / (pl.col("realized_volatility_60") + 1e-9)).alias("downside_vol_share"),
    ])
    df = df.with_columns([
        ((pl.col("high") / (pl.col("low") + 1e-9)).log() ** 2 / (4 * np.log(2))).rolling_mean(60).sqrt().alias("parkinson_vol_60"),
    ])
    df = df.with_columns([
        (pl.when((pl.col("open") > 0) & (pl.col("close") > 0) & (pl.col("high") > 0) & (pl.col("low") > 0))
         .then(
             0.5 * (pl.col("high") / (pl.col("low") + 1e-9)).log() ** 2
             - (2 * np.log(2) - 1) * (pl.col("close") / (pl.col("open") + 1e-9)).log() ** 2
         )
         .otherwise(0)
        ).rolling_mean(60).clip(lower_bound=0).sqrt().alias("garman_klass_vol_60"),
    ])
    return df


# ==================== 跳跃 ====================
def add_jump_factors(df: pl.DataFrame) -> pl.DataFrame:
    r = pl.col("ret").abs()
    r_prev = pl.col("ret").shift(1).abs()
    df = df.with_columns([
        (r * r_prev).rolling_sum(60).alias("bipower_variation_60"),
        (r ** 2).rolling_sum(60).alias("rv_60_abs"),
    ])
    df = df.with_columns([
        (pl.col("rv_60_abs") - pl.col("bipower_variation_60")).clip(lower_bound=0).alias("jump_variation_60"),
    ])
    df = df.with_columns([
        (pl.col("jump_variation_60") / (pl.col("rv_60_abs") + 1e-9)).alias("jump_ratio_60"),
    ])
    return df


# ==================== 流动性 ====================
def add_liquidity_factors(df: pl.DataFrame) -> pl.DataFrame:
    r = pl.col("ret").abs()
    df = df.with_columns([
        (r / (pl.col("volume") + 1e-9)).rolling_mean(60).alias("amihud_60"),
        (pl.col("ret") * pl.col("ret").shift(1)).rolling_mean(60).alias("ret_autocov_60"),
    ])
    df = df.with_columns([
        (2 * (-pl.col("ret_autocov_60")).clip(lower_bound=0).sqrt()).alias("roll_spread_60"),
    ])
    signed_vol = pl.col("buy_volume") - pl.col("sell_volume")
    df = df.with_columns(signed_vol.alias("signed_vol"))
    df = df.with_columns([
        (pl.col("ret") * pl.col("signed_vol")).rolling_mean(60).alias("ret_sv_cov_60"),
        (pl.col("signed_vol") ** 2).rolling_mean(60).alias("sv_var_60"),
    ])
    df = df.with_columns([
        (pl.col("ret_sv_cov_60") / (pl.col("sv_var_60") + 1e-9)).alias("kyle_lambda_60"),
    ])
    return df


# ==================== 订单簿 ====================
def add_orderbook_factors(df: pl.DataFrame,
                          bid_px, bid_sz, ask_px, ask_sz) -> pl.DataFrame:
    df = df.with_columns([
        pl.sum_horizontal([pl.col(c) for c in bid_sz[:5]]).alias("bid_vol_5"),
        pl.sum_horizontal([pl.col(c) for c in ask_sz[:5]]).alias("ask_vol_5"),
        pl.sum_horizontal([pl.col(c) for c in bid_sz]).alias("bid_vol_25"),
        pl.sum_horizontal([pl.col(c) for c in ask_sz]).alias("ask_vol_25"),
    ])
    df = df.with_columns([
        ((pl.col("bid_vol_25") - pl.col("ask_vol_25")) / (pl.col("bid_vol_25") + pl.col("ask_vol_25") + 1e-9)).alias("depth_imbalance"),
        (pl.col("bid_vol_5") / (pl.col("bid_vol_25") + 1e-9)).alias("depth_ratio_5_25_b"),
        ((pl.col("bids[0].amount") - pl.col("asks[0].amount")) / (pl.col("bids[0].amount") + pl.col("asks[0].amount") + 1e-9)).alias("book_pressure_1_b"),
        ((pl.col("bids[0].price") * pl.col("asks[0].amount") + pl.col("asks[0].price") * pl.col("bids[0].amount")) / (pl.col("bids[0].amount") + pl.col("asks[0].amount") + 1e-9)).alias("microprice"),
    ])
    df = df.with_columns([
        (pl.col("microprice") - pl.col("mid")).alias("microprice_dev_b"),
        ((pl.col("asks[24].price") - pl.col("bids[24].price")) / (pl.col("bid_vol_25") + pl.col("ask_vol_25") + 1e-9)).alias("quote_slope"),
        (pl.col("spread_bps") / (pl.col("bid_vol_25") + pl.col("ask_vol_25") + 1e-9)).alias("depth_adjusted_spread"),
    ])
    df = df.with_columns([
        (((pl.col("bid_vol_5") - pl.col("ask_vol_5")) / (pl.col("bid_vol_5") + pl.col("ask_vol_5") + 1e-9))
         - ((pl.col("bid_vol_25") - pl.col("ask_vol_25")) / (pl.col("bid_vol_25") + pl.col("ask_vol_25") + 1e-9))
        ).alias("deep_imbalance_5_25"),
    ])
    df = df.with_columns([
        ((pl.col("bids[4].price") - pl.col("bids[0].price")) / (pl.col("bid_vol_5") + 1e-9)).alias("book_slope_bid"),
        ((pl.col("asks[4].price") - pl.col("asks[0].price")) / (pl.col("ask_vol_5") + 1e-9)).alias("book_slope_ask"),
    ])
    df = df.with_columns([
        (pl.col("book_slope_bid") - pl.col("book_slope_ask")).alias("book_slope_diff"),
    ])
    return df


# ==================== 成交流 ====================
def add_trade_factors(df: pl.DataFrame) -> pl.DataFrame:
    df = df.with_columns([
        ((pl.col("buy_volume") - pl.col("sell_volume")) / (pl.col("buy_volume") + pl.col("sell_volume") + 1e-9)).alias("ofi_norm_b"),
        (pl.col("volume") / (pl.col("trade_count") + 1e-9)).alias("avg_trade_size_b"),
        (pl.col("buy_volume") / (pl.col("volume") + 1e-9)).alias("buy_trade_ratio_b"),
        (pl.col("trade_count") / 60.0).alias("trade_duration_intensity"),
    ])
    return df


# ==================== 增量（订单流） ====================
def add_incremental_factors(df: pl.DataFrame) -> pl.DataFrame:
    df = df.with_columns([
        (pl.col("bid_amount") / (pl.col("bid_amount") + pl.col("ask_amount") + 1e-9)).alias("add_bid_ratio"),
        (pl.col("ask_amount") / (pl.col("bid_amount") + pl.col("ask_amount") + 1e-9)).alias("add_ask_ratio"),
        ((pl.col("bid_amount") - pl.col("ask_amount")) / (pl.col("bid_amount") + pl.col("ask_amount") + 1e-9)).alias("net_add_imbalance"),
        (pl.col("total_amount") / (pl.col("event_count") + 1e-9)).alias("avg_event_size_b"),
    ])
    return df


# ==================== 反转 ====================
def add_reversal_factors(df: pl.DataFrame) -> pl.DataFrame:
    df = df.with_columns([
        (-pl.col("ret").rolling_sum(60)).alias("return_reversal_60"),
        (-(pl.col("ret") * pl.col("volume")).rolling_sum(60) / (pl.col("volume").rolling_sum(60) + 1e-9)).alias("volume_weighted_reversal_60"),
        ((pl.col("ret") == 0).cast(pl.Float64).rolling_mean(60)).alias("tick_discreteness"),
    ])
    return df


# ==================== 新增 15 个因子 ====================
def add_extra_factors(df: pl.DataFrame) -> pl.DataFrame:
    """基于行为金融 + 微观结构理论新增的 15 个因子"""

    # --- 1. 波动率调整反转 ---
    df = df.with_columns([
        (-pl.col("ret").rolling_sum(60) / (pl.col("realized_volatility_60") + 1e-9)).alias("vol_adj_reversal_60"),
    ])

    # --- 2. 锚定偏离 ---
    df = df.with_columns([
        (pl.col("mid") / (pl.col("mid").rolling_mean(60) + 1e-9) - 1).alias("anchoring_deviation_60"),
    ])

    # --- 3. 处置效应压力 ---
    df = df.with_columns([
        ((pl.col("mid") - pl.col("mid").rolling_max(60)) / (pl.col("mid") + 1e-9)).alias("disposition_pressure_60"),
    ])

    # --- 4. 成交情绪 ---
    df = df.with_columns([
        (pl.col("buy_volume") / (pl.col("volume") + 1e-9)).alias("trading_sentiment"),
    ])

    # --- 5. 极端成交 ---
    df = df.with_columns([
        ((pl.col("volume") - pl.col("volume").rolling_mean(60)) / (pl.col("volume").rolling_std(60) + 1e-9)).alias("extreme_trading_60"),
    ])

    # --- 6. 收益率自相关 ---
    df = df.with_columns([
        (pl.col("ret") * pl.col("ret").shift(1)).rolling_mean(60).alias("ret_autocorr_60"),
    ])

    # --- 7. 成交量自相关 ---
    df = df.with_columns([
        (pl.col("volume") * pl.col("volume").shift(1)).rolling_mean(60).alias("vol_autocorr_60"),
    ])

    # --- 8. 成交量分布偏度 ---
    df = df.with_columns([
        (((pl.col("volume") - pl.col("volume").rolling_mean(60)) ** 3).rolling_mean(60)
         / (pl.col("volume").rolling_std(60) ** 3 + 1e-9)).alias("volume_skewness_60"),
    ])

    # --- 9. 日内位置 ---
    df = df.with_columns([
        (pl.col("ts").dt.hour() * 60 + pl.col("ts").dt.minute()).cast(pl.Float64).alias("minute_of_day"),
    ])

    # --- 10. 深度调整反转 ---
    df = df.with_columns([
        (-pl.col("ret").rolling_sum(60) * pl.col("depth_imbalance")).alias("depth_adj_reversal_60"),
    ])

    # --- 11. 订单流毒性（VPIN 简化版） ---
    df = df.with_columns([
        ((pl.col("buy_volume") - pl.col("sell_volume")).abs().rolling_mean(60)
         / (pl.col("volume").rolling_mean(60) + 1e-9)).alias("vpin_60"),
    ])

    # --- 12. 价差波动比 ---
    df = df.with_columns([
        (pl.col("spread_bps") / (pl.col("realized_volatility_60") * 1e4 + 1e-9)).alias("spread_to_vol_ratio"),
    ])

    # --- 13. 大单压力（用 1 秒成交量近似） ---
    df = df.with_columns([
        ((pl.col("volume") - pl.col("volume").rolling_mean(60)) / (pl.col("volume").rolling_std(60) + 1e-9)
         * pl.col("buy_trade_ratio_b")).alias("large_trade_pressure"),
    ])

    # --- 14. 深度变化率 ---
    df = df.with_columns([
        ((pl.col("bid_vol_25") + pl.col("ask_vol_25")).pct_change()).alias("depth_change_rate"),
    ])

    # --- 15. 综合买卖压力 ---
    df = df.with_columns([
        (0.4 * pl.col("depth_imbalance")
         + 0.3 * pl.col("book_pressure_1_b")
         + 0.3 * pl.col("net_add_imbalance")).alias("composite_pressure"),
    ])

    return df


# ==================== Step 1: CSV -> Parquet ====================
def convert_csv_to_parquet(date: str):
    for name in ["trades", "book_snapshot_25", "incremental_book_L2"]:
        src = DATA / f"{name}_{date}.csv"
        dst = DATA / f"{name}_{date}.parquet"
        if not src.exists():
            print(f"  跳过（不存在）: {src.name}")
            continue
        if dst.exists():
            print(f"  已存在: {dst.name}")
            continue
        print(f"  转换 {src.name} ...")
        pl.scan_csv(src, infer_schema_length=10000).sink_parquet(dst)
        print(f"    -> {dst.name}")


# ==================== Step 2: 聚合成 1 秒 bar ====================
def build_bars(date: str):
    trades_p = DATA / f"trades_{date}.parquet"
    snaps_p  = DATA / f"book_snapshot_25_{date}.parquet"
    inc_p    = DATA / f"incremental_book_L2_{date}.parquet"

    if trades_p.exists() and not (DATA / f"trade_bars_{date}.parquet").exists():
        print(f"  trades bars ...")
        trade_bars = (
            pl.scan_parquet(trades_p)
              .with_columns(pl.col("timestamp").cast(pl.Datetime("us")).alias("ts"))
              .group_by_dynamic("ts", every="1s")
              .agg([
                  pl.col("price").first().alias("open"),
                  pl.col("price").max().alias("high"),
                  pl.col("price").min().alias("low"),
                  pl.col("price").last().alias("close"),
                  pl.col("amount").sum().alias("volume"),
                  pl.col("price").count().alias("trade_count"),
                  pl.when(pl.col("side") == "buy").then(pl.col("amount")).otherwise(0).sum().alias("buy_volume"),
                  pl.when(pl.col("side") == "sell").then(pl.col("amount")).otherwise(0).sum().alias("sell_volume"),
              ])
              .collect(engine="streaming")
        )
        trade_bars.write_parquet(DATA / f"trade_bars_{date}.parquet")

    if snaps_p.exists() and not (DATA / f"snapshot_bars_{date}.parquet").exists():
        print(f"  snapshot bars ...")
        snapshot_bars = (
            pl.scan_parquet(snaps_p)
              .with_columns(pl.col("timestamp").cast(pl.Datetime("us")).alias("ts"))
              .group_by_dynamic("ts", every="1s")
              .agg(pl.all().last())
              .collect(engine="streaming")
        )
        snapshot_bars.write_parquet(DATA / f"snapshot_bars_{date}.parquet")

    if inc_p.exists() and not (DATA / f"incremental_bars_{date}.parquet").exists():
        print(f"  incremental bars ...")
        inc_bars = (
            pl.scan_parquet(inc_p)
              .with_columns(pl.col("timestamp").cast(pl.Datetime("us")).alias("ts"))
              .group_by_dynamic("ts", every="1s")
              .agg([
                  pl.len().alias("event_count"),
                  pl.col("amount").sum().alias("total_amount"),
                  pl.when(pl.col("side") == "bid").then(pl.col("amount")).otherwise(0).sum().alias("bid_amount"),
                  pl.when(pl.col("side") == "ask").then(pl.col("amount")).otherwise(0).sum().alias("ask_amount"),
                  pl.col("is_snapshot").sum().alias("snapshot_events"),
              ])
              .collect(engine="streaming")
        )
        inc_bars.write_parquet(DATA / f"incremental_bars_{date}.parquet")


# ==================== Step 3: 算因子 ====================
def build_factors(date: str):
    out = OUT_FACTORS / f"factors_{date}.parquet"
    if out.exists():
        print(f"  因子已存在: {out.name}（如需重算，先删除）")
        return

    snaps  = pl.read_parquet(DATA / f"snapshot_bars_{date}.parquet")
    trades = pl.read_parquet(DATA / f"trade_bars_{date}.parquet")
    inc    = pl.read_parquet(DATA / f"incremental_bars_{date}.parquet")

    bid_px = [f"bids[{i}].price"  for i in range(25)]
    bid_sz = [f"bids[{i}].amount" for i in range(25)]
    ask_px = [f"asks[{i}].price"  for i in range(25)]
    ask_sz = [f"asks[{i}].amount" for i in range(25)]

    snaps = snaps.with_columns([
        ((pl.col("bids[0].price") + pl.col("asks[0].price")) / 2).alias("mid"),
        (pl.col("asks[0].price") - pl.col("bids[0].price")).alias("spread"),
    ]).with_columns([
        (pl.col("spread") / pl.col("mid") * 1e4).alias("spread_bps"),
    ])

    df = (snaps
          .join(trades.select(["ts", "open", "high", "low", "close",
                               "volume", "trade_count", "buy_volume", "sell_volume"]),
                on="ts", how="left")
          .join(inc.select(["ts", "event_count", "total_amount", "bid_amount", "ask_amount"]),
                on="ts", how="left")
          .fill_null(0))

    df = df.with_columns(pl.col("mid").pct_change().alias("ret"))

    # 原有 40 个
    df = add_volatility_factors(df)
    df = add_jump_factors(df)
    df = add_liquidity_factors(df)
    df = add_orderbook_factors(df, bid_px, bid_sz, ask_px, ask_sz)
    df = add_trade_factors(df)
    df = add_incremental_factors(df)
    df = add_reversal_factors(df)

    # 新增 15 个
    df = add_extra_factors(df)

    # 目标
    df = df.with_columns(pl.col("mid").shift(-TARGET_HORIZON).alias("mid_fwd"))
    df = df.with_columns((pl.col("mid_fwd") / pl.col("mid") - 1).alias("target"))

    keep_cols = [
        "ts", "mid", "spread", "spread_bps", "ret", "mid_fwd", "target",
        # 订单簿
        "depth_imbalance", "microprice_dev_b", "book_pressure_1_b",
        "depth_ratio_5_25_b", "quote_slope", "depth_adjusted_spread",
        "deep_imbalance_5_25", "book_slope_bid", "book_slope_ask", "book_slope_diff",
        # 波动率
        "realized_volatility_60", "realized_volatility_300",
        "realized_skewness_60", "realized_kurtosis_60",
        "upside_volatility_60", "downside_volatility_60",
        "rv_ratio", "downside_vol_share",
        "parkinson_vol_60", "garman_klass_vol_60",
        # 跳跃
        "bipower_variation_60", "jump_variation_60", "jump_ratio_60",
        # 流动性
        "amihud_60", "ret_autocov_60", "roll_spread_60",
        "kyle_lambda_60", "signed_vol", "sv_var_60", "ret_sv_cov_60",
        # 成交流
        "ofi_norm_b", "avg_trade_size_b", "buy_trade_ratio_b", "trade_duration_intensity",
        # 增量
        "add_bid_ratio", "add_ask_ratio", "net_add_imbalance", "avg_event_size_b",
        # 反转
        "return_reversal_60", "volume_weighted_reversal_60", "tick_discreteness",
        # 新增 15 个
        "vol_adj_reversal_60", "anchoring_deviation_60", "disposition_pressure_60",
        "trading_sentiment", "extreme_trading_60", "ret_autocorr_60",
        "vol_autocorr_60", "volume_skewness_60", "minute_of_day",
        "depth_adj_reversal_60", "vpin_60", "spread_to_vol_ratio",
        "large_trade_pressure", "depth_change_rate", "composite_pressure",
        # OHLC 和成交量
        "open", "high", "low", "close",
        "volume", "trade_count", "buy_volume", "sell_volume",
        "event_count", "total_amount", "bid_amount", "ask_amount",
    ]
    df = df.select([c for c in keep_cols if c in df.columns])

    df.write_parquet(out)
    print(f"  因子已存: {out.name}  shape={df.shape}")


# ==================== Step 4: IC 分析 ====================
def analyze_ic(dates):
    rows = []
    for date in dates:
        f = OUT_FACTORS / f"factors_{date}.parquet"
        if not f.exists():
            continue
        df = pl.read_parquet(f).to_pandas()
        if "ts" in df.columns:
            df = df.set_index("ts")
        df = df.dropna(subset=["target"])

        exclude = {"target", "mid_fwd", "date", "ret", "mid", "open", "high", "low", "close"}
        feats = [c for c in df.columns
                 if c not in exclude
                 and df[c].dtype in ("float64", "float32", "int64", "int32")]

        for c in feats:
            sub = df[[c, "target"]].dropna()
            if len(sub) < 100 or sub[c].std() == 0:
                continue
            ic = spearmanr(sub[c], sub["target"]).correlation
            if np.isnan(ic):
                continue
            rows.append({"date": date, "factor": c, "ic": ic, "n": len(sub)})

    if not rows:
        print("没有可用因子")
        return

    ic_df = pd.DataFrame(rows)
    summary = (ic_df.groupby("factor")["ic"]
                    .agg(["mean", "std", "min", "max", "count"])
                    .rename(columns={"mean": "IC_mean", "std": "IC_std",
                                     "min": "IC_min", "max": "IC_max",
                                     "count": "days"}))
    summary["ICIR"] = summary["IC_mean"] / (summary["IC_std"] + 1e-9)
    summary["abs_IC_mean"] = summary["IC_mean"].abs()
    summary = summary.sort_values("abs_IC_mean", ascending=False)

    print("\n================ 单因子 IC 汇总 ================")
    print(summary.to_string(float_format=lambda x: f"{x:+.4f}"))

    summary.to_csv(DATA / "ic_summary.csv")
    ic_df.pivot(index="date", columns="factor", values="ic").to_csv(DATA / "ic_by_day.csv")
    print("\n已保存: ic_summary.csv, ic_by_day.csv")


# ==================== Step 5: 相关性分析 ====================
def analyze_corr(dates):
    """算候选因子的两两相关系数，用于去重"""
    CANDIDATES = [
        # 订单簿
        "depth_imbalance", "microprice_dev_b", "book_pressure_1_b",
        "depth_ratio_5_25_b", "book_slope_bid", "book_slope_ask", "book_slope_diff",
        "deep_imbalance_5_25", "quote_slope", "depth_adjusted_spread",
        # 波动率
        "realized_volatility_60", "realized_volatility_300",
        "realized_skewness_60", "realized_kurtosis_60",
        "upside_volatility_60", "downside_volatility_60",
        "rv_ratio", "downside_vol_share", "parkinson_vol_60", "garman_klass_vol_60",
        # 跳跃
        "jump_ratio_60", "jump_variation_60",
        # 流动性
        "amihud_60", "ret_autocov_60", "roll_spread_60",
        "kyle_lambda_60", "signed_vol", "sv_var_60",
        # 成交流
        "ofi_norm_b", "avg_trade_size_b", "buy_trade_ratio_b", "trade_duration_intensity",
        # 增量
        "net_add_imbalance", "avg_event_size_b",
        # 反转
        "return_reversal_60", "volume_weighted_reversal_60",
        "vol_adj_reversal_60", "depth_adj_reversal_60",
        # 新增
        "anchoring_deviation_60", "disposition_pressure_60",
        "trading_sentiment", "extreme_trading_60", "ret_autocorr_60",
        "vol_autocorr_60", "volume_skewness_60", "vpin_60",
        "spread_to_vol_ratio", "large_trade_pressure",
        "depth_change_rate", "composite_pressure",
    ]
    f = OUT_FACTORS / f"factors_{dates[0]}.parquet"
    if not f.exists():
        print("没有因子文件")
        return
    df = pl.read_parquet(f).to_pandas()
    if "ts" in df.columns:
        df = df.set_index("ts")
    df = df.dropna(subset=["target"])

    cand = [c for c in CANDIDATES if c in df.columns]
    corr = df[cand].corr()
    print(f"\n================ 候选因子相关性（{len(cand)} 个） ================")
    print(corr.round(3).to_string())
    corr.to_csv(DATA / "factor_corr.csv")

    # 打印高相关对（|r| > 0.8）
    print("\n================ 高相关因子对（|r| > 0.8） ================")
    n = len(cand)
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            r = corr.iloc[i, j]
            if abs(r) > 0.8:
                pairs.append((cand[i], cand[j], r))
    if pairs:
        for a, b, r in sorted(pairs, key=lambda x: -abs(x[2])):
            print(f"  {a:30s} <-> {b:30s}  r={r:+.3f}")
    else:
        print("  没有高相关对")


# ==================== Step 6: 多因子组合回测 ====================
def backtest_combo(dates, n_top=8):
    """
    用 IC 最高的 N 个因子做等权组合，方向按 IC 符号，
    计算多空收益，扣手续费。
    """
    f = OUT_FACTORS / f"factors_{dates[0]}.parquet"
    if not f.exists():
        print("没有因子文件")
        return
    df = pl.read_parquet(f).to_pandas()
    if "ts" in df.columns:
        df = df.set_index("ts")
    df = df.dropna(subset=["target"])

    # 读 IC 汇总，选 IC 最高的 N 个（去掉高度相关的）
    ic_path = DATA / "ic_summary.csv"
    if not ic_path.exists():
        print("先跑 analyze_ic")
        return
    ic_sum = pd.read_csv(ic_path)
    ic_sum = ic_sum[~ic_sum["factor"].isin(
        ["mid", "spread", "ret", "mid_fwd", "target",
         "open", "high", "low", "close", "volume",
         "trade_count", "buy_volume", "sell_volume",
         "event_count", "total_amount", "bid_amount", "ask_amount",
         "minute_of_day", "signed_vol", "sv_var_60", "ret_sv_cov_60",
         "book_slope_diff", "add_bid_ratio", "add_ask_ratio",
         "bipower_variation_60", "rv_60_abs"]
    )]
    ic_sum = ic_sum.head(n_top)
    selected = ic_sum["factor"].tolist()
    signs = np.sign(ic_sum["IC_mean"].values)

    print(f"\n================ 多因子组合（Top {len(selected)}） ================")
    for fac, s in zip(selected, signs):
        print(f"  {fac:30s}  方向={'+' if s>0 else '-'}")

    # 标准化因子
    X = df[selected].values
    X = (X - np.nanmean(X, axis=0)) / (np.nanstd(X, axis=0) + 1e-9)
    X = np.nan_to_num(X)

    # 等权组合
    signal = (X * signs).mean(axis=1)
    signal = np.sign(signal)  # 只做方向

    pnl_gross = signal * df["target"].values
    turnover = np.abs(np.diff(signal, prepend=signal[0]))
    pnl_net = pnl_gross - turnover * FEE_RATE

    print(f"\n毛收益: {pnl_gross.sum():.6f}")
    print(f"净收益: {pnl_net.sum():.6f}")
    print(f"手续费: {turnover.sum() * FEE_RATE:.6f}")
    print(f"胜率: {(pnl_net > 0).mean():.2%}")
    print(f"夏普: {pnl_net.mean() / (pnl_net.std() + 1e-9) * np.sqrt(86400):.4f}")

    # 存结果
    out = pd.DataFrame({"pnl_gross": pnl_gross, "pnl_net": pnl_net}, index=df.index)
    out.to_parquet(DATA / "combo_pnl.parquet")
    print("\n已保存: combo_pnl.parquet")


# ==================== 主流程 ====================
def main():
    print("=" * 60)
    print("Pipeline: CSV -> Parquet -> Bars -> Factors(55) -> IC -> Corr -> Combo")
    print("=" * 60)

    for date in DATES:
        print(f"\n---------- {date} ----------")
        print("[1/3] CSV -> Parquet")
        convert_csv_to_parquet(date)
        print("[2/3] 聚合成 1 秒 bar")
        build_bars(date)
        print("[3/3] 算因子")
        try:
            build_factors(date)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  因子计算失败: {e}")

    print("\n" + "=" * 60)
    print("IC 分析")
    print("=" * 60)
    analyze_ic(DATES)

    print("\n" + "=" * 60)
    print("相关性分析")
    print("=" * 60)
    analyze_corr(DATES)

    print("\n" + "=" * 60)
    print("多因子组合回测")
    print("=" * 60)
    backtest_combo(DATES, n_top=8)


if __name__ == "__main__":
    main()