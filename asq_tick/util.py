"""Helpers shared by the ASQ tick market maker."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Any

from asq_tick.nt_compat import Price, Quantity


def as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def make_price(instrument: Any, value: float | Decimal) -> Price:
    if hasattr(instrument, "make_price"):
        return instrument.make_price(as_decimal(value))
    quantized = round(float(value), instrument.price_precision)
    return Price(quantized, instrument.price_precision)


def make_qty(instrument: Any, value: float | Decimal) -> Quantity:
    qty = as_decimal(value)
    increment = as_decimal(instrument.size_increment)
    if increment > 0:
        steps = (qty / increment).to_integral_value(rounding=ROUND_DOWN)
        qty = steps * increment
    precision = instrument.size_precision
    if hasattr(instrument, "make_qty"):
        return instrument.make_qty(qty)
    return Quantity(float(qty), precision)


def min_qty(instrument: Any) -> Decimal:
    raw = getattr(instrument, "min_quantity", None)
    if raw is None:
        return as_decimal(instrument.size_increment)
    return as_decimal(raw)


def min_notional(instrument: Any) -> Decimal:
    raw = getattr(instrument, "min_notional", None)
    if raw is None:
        return Decimal("0")
    if hasattr(raw, "as_decimal"):
        return as_decimal(raw.as_decimal())
    return Decimal(str(raw).split()[0])


def qty_for_notional(instrument: Any, price: float | Decimal, notional_usd: float | Decimal) -> Decimal:
    """Size a clip so the notional still meets the floor after lot rounding."""
    px = as_decimal(price)
    if px <= 0:
        return Decimal("0")
    target = max(as_decimal(notional_usd), min_notional(instrument))
    qty = target / px
    increment = as_decimal(instrument.size_increment)
    if increment > 0:
        qty = (qty / increment).to_integral_value(rounding=ROUND_UP) * increment
    floor = min_qty(instrument)
    if qty < floor:
        qty = floor
    if qty * px + Decimal("1e-12") < target:
        qty += increment
    return qty


def tick_size(instrument: Any) -> float:
    return float(instrument.price_increment)


def quote_prices(tick) -> tuple[float, float, float, float]:
    bid = float(getattr(tick, "bid_price", None) or getattr(tick, "bid"))
    ask = float(getattr(tick, "ask_price", None) or getattr(tick, "ask"))
    bid_size = float(getattr(tick, "bid_size"))
    ask_size = float(getattr(tick, "ask_size"))
    return bid, ask, bid_size, ask_size
