"""Convert tick DataFrames into Nautilus TradeTick / QuoteTick objects."""

from __future__ import annotations

from typing import Any

import pandas as pd

from crypto_tick.nt_compat import AggressorSide, QuoteTick, TradeId, TradeTick
from crypto_tick.util import make_price, make_qty


def frames_to_nautilus(instrument: Any, frame: pd.DataFrame) -> tuple[list, list]:
    trades: list = []
    quotes: list = []
    for i, row in enumerate(frame.itertuples(index=False), start=1):
        ts = int(row.timestamp_ns)
        price = make_price(instrument, row.price)
        size = make_qty(instrument, row.size)
        side = AggressorSide.BUYER if str(row.aggressor).upper() == "BUYER" else AggressorSide.SELLER
        trades.append(_trade_tick(instrument, price, size, side, str(i), ts))
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
    return trades, quotes


def quotes_from_tob(instrument: Any, frame: pd.DataFrame) -> list:
    """Build QuoteTicks from a top-of-book frame produced by `data_l2`."""
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


def _trade_tick(instrument, price, size, side, trade_id: str, ts: int):
    kwargs_options = [
        dict(
            instrument_id=instrument.id,
            price=price,
            size=size,
            aggressor_side=side,
            trade_id=TradeId(trade_id),
            ts_event=ts,
            ts_init=ts,
        ),
        dict(
            instrument_id=instrument.id,
            price=price,
            quantity=size,
            aggressor_side=side,
            trade_id=TradeId(trade_id),
            ts_event=ts,
            ts_init=ts,
        ),
    ]
    last_error: Exception | None = None
    for kwargs in kwargs_options:
        try:
            return TradeTick(**kwargs)
        except TypeError as exc:
            last_error = exc
    raise TypeError(f"Could not construct TradeTick: {last_error}") from last_error


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
