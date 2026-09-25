# run.py
import pandas as pd
import numpy as np
from pathlib import Path
from utils_v2 import agg_data
from backtest import back_test_Q

DATA = Path(r"J:\l2data")
DATE = "2026-09-04"
PRICE_INT = 0.01
TIME_STEP = 1000


def main():
    factors = pd.read_parquet(DATA / "factors" / f"factors_{DATE}.parquet").set_index("ts")
    print("因子表 shape:", factors.shape)

    out = pd.DataFrame(index=factors.index)

    out[("bp", "last")] = factors["mid"] - factors["spread"] / 2
    out[("ap", "last")] = factors["mid"] + factors["spread"] / 2
    out[("bp", "max")] = out[("bp", "last")]
    out[("bp", "min")] = out[("bp", "last")]
    out[("ap", "max")] = out[("ap", "last")]
    out[("ap", "min")] = out[("ap", "last")]
    out[("mid", "")] = factors["mid"]
    out[("ret", "")] = factors["mid"].pct_change()

    out[("bv", "sum")] = factors.get("bid_vol_25", 0)
    out[("av", "sum")] = factors.get("ask_vol_25", 0)
    out[("bv", "last")] = factors.get("bid_vol_5", 0)
    out[("av", "last")] = factors.get("ask_vol_5", 0)

    out[("tv", "sum")] = factors.get("volume", 0)
    out[("qty", "sum")] = factors.get("trade_count", 0)
    out[("tbv", "sum")] = factors.get("buy_volume", 0)
    out[("tsv", "sum")] = factors.get("sell_volume", 0)
    out[("bamt", "sum")] = factors.get("bid_amount", 0)
    out[("aamt", "sum")] = factors.get("ask_amount", 0)
    out[("ecnt", "sum")] = factors.get("event_count", 0)

    factor_cols = [
        "depth_imbalance", "book_slope_bid", "spread_bps",
        "depth_ratio_5_25_b", "realized_volatility_60", "garman_klass_vol_60",
        "ret_autocov_60", "net_add_imbalance", "amihud_60",
        "vpin_60", "ofi_norm_b", "buy_trade_ratio_b",
        "minute_of_day",
    ]
    for c in factor_cols:
        if c in factors.columns:
            out[c] = factors[c].values

    out.index.name = "ms-index"
    # === 关键：把 DatetimeIndex 转成整数毫秒 ===
    out.index = (out.index.astype("int64") // 1_000_000).astype("int64")
    print("转换后 shape:", out.shape)
    print("index dtype:", out.index.dtype)
    print("列名前 20 个:", out.columns.tolist()[:20])

    back_test_Q(out, price_int=PRICE_INT, time_step=TIME_STEP,
                split_ratio=0.7, gamma=0.01, Q=10, fee_rate=2e-4)


if __name__ == "__main__":
    main()
