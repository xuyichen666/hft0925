"""Replay Tardis-style incremental L2 CSVs into a top-of-book series.

Input columns (binance-futures dumps):
    exchange, symbol, timestamp, local_timestamp, is_snapshot, side, price, amount

`amount == 0` deletes a level. Rows flagged `is_snapshot` start a fresh book.
The whole file is replayed in order because a correct best bid/ask needs every
level, but only throttled top-of-book changes are written out.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TOB_COLUMNS = ["timestamp_ns", "bid", "ask", "bid_size", "ask_size"]
_USECOLS = ["timestamp", "is_snapshot", "side", "price", "amount"]


@dataclass
class L2Options:
    throttle_ms: int = 100
    skip_minutes: float = 0.0
    minutes: float | None = None
    chunk_rows: int = 2_000_000


class _BookSide:
    """Price -> size map with a lazily cleaned heap for the touch level."""

    def __init__(self, is_bid: bool) -> None:
        self._sign = -1.0 if is_bid else 1.0
        self._levels: dict[float, float] = {}
        self._heap: list[float] = []
        self._queued: set[float] = set()

    def clear(self) -> None:
        self._levels.clear()
        self._heap.clear()
        self._queued.clear()

    def update(self, price: float, size: float) -> None:
        if size <= 0.0:
            self._levels.pop(price, None)
            return
        self._levels[price] = size
        if price not in self._queued:
            heapq.heappush(self._heap, self._sign * price)
            self._queued.add(price)

    def best(self) -> tuple[float, float] | None:
        while self._heap:
            price = self._sign * self._heap[0]
            size = self._levels.get(price)
            if size:
                return price, size
            heapq.heappop(self._heap)
            self._queued.discard(price)
        return None


def replay_to_tob(path: str | Path, options: L2Options | None = None) -> pd.DataFrame:
    """Return a DataFrame of throttled top-of-book updates."""
    opts = options or L2Options()
    bids = _BookSide(is_bid=True)
    asks = _BookSide(is_bid=False)

    throttle_us = opts.throttle_ms * 1_000
    rows: list[tuple[int, float, float, float, float]] = []
    pending_ts: int | None = None
    last_emit_us = -throttle_us
    last_top: tuple[float, float, float, float] | None = None
    in_snapshot = False

    start_us: int | None = None
    skip_until_us: int | None = None
    stop_us: int | None = None

    def flush(ts_us: int) -> None:
        nonlocal last_emit_us, last_top
        if skip_until_us is not None and ts_us < skip_until_us:
            return
        if ts_us - last_emit_us < throttle_us:
            return
        best_bid = bids.best()
        best_ask = asks.best()
        if best_bid is None or best_ask is None or best_bid[0] >= best_ask[0]:
            return
        top = (best_bid[0], best_ask[0], best_bid[1], best_ask[1])
        if top == last_top:
            return
        rows.append((ts_us * 1_000, *top))
        last_top = top
        last_emit_us = ts_us

    reader = pd.read_csv(
        path,
        usecols=_USECOLS,
        chunksize=opts.chunk_rows,
        dtype={"timestamp": "int64", "side": "str", "price": "float64", "amount": "float64"},
    )
    for chunk in reader:
        timestamps = chunk["timestamp"].to_numpy()
        snapshots = _as_bool(chunk["is_snapshot"])
        sides = chunk["side"].to_numpy()
        prices = chunk["price"].to_numpy()
        amounts = chunk["amount"].to_numpy()

        if start_us is None:
            start_us = int(timestamps[0])
            skip_until_us = start_us + int(opts.skip_minutes * 60_000_000)
            if opts.minutes is not None:
                stop_us = skip_until_us + int(opts.minutes * 60_000_000)

        for ts, is_snap, side, price, amount in zip(
            timestamps, snapshots, sides, prices, amounts
        ):
            ts = int(ts)
            if stop_us is not None and ts > stop_us:
                if pending_ts is not None:
                    flush(pending_ts)
                return _to_frame(rows)

            if is_snap and not in_snapshot:
                bids.clear()
                asks.clear()
            in_snapshot = bool(is_snap)

            if pending_ts is not None and ts != pending_ts:
                flush(pending_ts)
            pending_ts = ts

            if side == "bid":
                bids.update(price, amount)
            else:
                asks.update(price, amount)

    if pending_ts is not None:
        flush(pending_ts)
    return _to_frame(rows)


def _as_bool(series: pd.Series):
    if series.dtype == bool:
        return series.to_numpy()
    return (series.astype(str).str.upper() == "TRUE").to_numpy()


def _to_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=TOB_COLUMNS)


def save_tob(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def load_tob(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = set(TOB_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing columns {sorted(missing)}")
    return frame
