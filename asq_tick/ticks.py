"""Convert top-of-book frames into Nautilus QuoteTick objects."""

from __future__ import annotations

from typing import Any

import pandas as pd

from asq_tick.nt_compat import QuoteTick
from asq_tick.util import make_price, make_qty


def quotes_from_tob(instrument: Any, frame: pd.DataFrame) -> list:
    quotes: list = []
    for row in frame.itertuples(index=False):
        ts = int(row.timestamp_ns)
        quotes.append(
            _quote_tick(
                instrument,
                make_price(instrument, row.bid),
                make_price(instrument, row.ask),
                make_qty(instrument, row.bid_size),
                make_qty(instrument, row.ask_size),
                ts,
            )
        )
    return quotes


def slice_tob(frame: pd.DataFrame, minutes: float | None = None, skip_minutes: float = 0.0) -> pd.DataFrame:
    if frame.empty:
        return frame
    start = int(frame.timestamp_ns.iloc[0]) + int(skip_minutes * 60 * 1_000_000_000)
    out = frame[frame.timestamp_ns >= start]
    if minutes is not None:
        stop = start + int(minutes * 60 * 1_000_000_000)
        out = out[out.timestamp_ns <= stop]
    return out.reset_index(drop=True)


def _quote_tick(instrument, bid, ask, bid_size, ask_size, ts: int):
    kwargs_options = [
        dict(
            instrument_id=instrument.id,
            bid_price=bid,
            ask_price=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            ts_event=ts,
            ts_init=ts,
        ),
        dict(
            instrument_id=instrument.id,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            ts_event=ts,
            ts_init=ts,
        ),
    ]
    last_error: Exception | None = None
    for kwargs in kwargs_options:
        try:
            return QuoteTick(**kwargs)
        except TypeError as exc:
            last_error = exc
    raise TypeError(f"Could not construct QuoteTick: {last_error}") from last_error
