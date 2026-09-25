"""Helpers shared by the crypto tick pair trader."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any

from crypto_tick.nt_compat import (
    AggregationSource,
    BarSpecification,
    BarType,
    InstrumentId,
    Price,
    Quantity,
)


def make_bar_type(instrument_id: InstrumentId, bar_spec: str, internal: bool = True) -> BarType:
    spec = BarSpecification.from_str(bar_spec)
    source = AggregationSource.INTERNAL if internal else AggregationSource.EXTERNAL
    return BarType(instrument_id=instrument_id, bar_spec=spec, aggregation_source=source)


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


def round_down_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    if increment <= 0:
        return value
    steps = (value / increment).to_integral_value(rounding=ROUND_DOWN)
    return steps * increment
