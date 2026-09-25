"""Download Binance USD-M perpetual aggTrades without an API key."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

FAPI_AGG_TRADES = "https://fapi.binance.com/fapi/v1/aggTrades"


def download_agg_trades(
    symbol: str,
    start_ms: int,
    end_ms: int,
    pause_s: float = 0.15,
) -> pd.DataFrame:
    """Fetch aggTrades for a native Binance futures symbol, e.g. BTCUSDT."""
    rows: list[dict] = []
    cursor = start_ms
    while cursor < end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        url = f"{FAPI_AGG_TRADES}?{params}"
        with urllib.request.urlopen(url, timeout=30) as response:
            batch = json.loads(response.read().decode("utf-8"))
        if not batch:
            break
        rows.extend(batch)
        last_time = int(batch[-1]["T"])
        if last_time <= cursor:
            break
        cursor = last_time + 1
        time.sleep(pause_s)
    if not rows:
        return pd.DataFrame(columns=["timestamp_ns", "price", "size", "aggressor", "bid", "ask", "bid_size", "ask_size"])
    return agg_trades_to_frame(rows)


def agg_trades_to_frame(rows: list[dict]) -> pd.DataFrame:
    prices = np_float([row["p"] for row in rows])
    sizes = np_float([row["q"] for row in rows])
    ts_ns = [int(row["T"]) * 1_000_000 for row in rows]
    # Binance m=True means buyer is maker => seller was aggressor.
    aggressor = ["SELLER" if row["m"] else "BUYER" for row in rows]
    # Reconstruct a 1-tick spread around the trade for L1 matching.
    tick_size = _infer_tick(prices)
    half = tick_size / 2.0
    bid = prices - half
    ask = prices + half
    return pd.DataFrame(
        {
            "timestamp_ns": ts_ns,
            "price": prices,
            "size": sizes,
            "aggressor": aggressor,
            "bid": bid,
            "ask": ask,
            "bid_size": sizes,
            "ask_size": sizes,
        }
    )


def np_float(values) -> list[float]:
    return [float(v) for v in values]


def _infer_tick(prices: list[float]) -> float:
    if not prices:
        return 0.01
    sample = prices[: min(len(prices), 200)]
    decimals = max(len(str(p).split(".")[-1]) if "." in str(p) else 0 for p in sample)
    return 10 ** (-max(decimals, 1))


def save_downloaded(symbol: str, frame: pd.DataFrame, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{symbol.lower()}_perp_ticks.csv"
    frame.to_csv(path, index=False)
    return path
