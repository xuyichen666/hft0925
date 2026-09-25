"""Import shims for nautilus_trader 1.169 through 1.222."""

from __future__ import annotations

import importlib.util
import sys
from typing import Any


def _import_first(candidates: list[tuple[str, str]]) -> Any:
    last_error: Exception | None = None
    for module_name, attr in candidates:
        try:
            module = __import__(module_name, fromlist=[attr])
            return getattr(module, attr)
        except (ImportError, AttributeError) as exc:
            last_error = exc

    if importlib.util.find_spec("nautilus_trader") is None:
        raise ImportError(
            f"nautilus_trader is not installed for {sys.executable} "
            f"(Python {sys.version.split()[0]}). Run this with the interpreter that has it, "
            "or install it: pip install -r crypto_tick/requirements.txt"
        ) from last_error
    raise ImportError(f"Could not import {candidates!r}") from last_error


Actor = _import_first(
    [
        ("nautilus_trader.common.actor", "Actor"),
        ("nautilus_trader.common", "Actor"),
    ]
)
ActorConfig = _import_first(
    [
        ("nautilus_trader.common.actor", "ActorConfig"),
        ("nautilus_trader.common.config", "ActorConfig"),
        ("nautilus_trader.config", "ActorConfig"),
        ("nautilus_trader.common", "ActorConfig"),
    ]
)
LogColor = _import_first(
    [
        ("nautilus_trader.common.enums", "LogColor"),
        ("nautilus_trader.common", "LogColor"),
    ]
)
Strategy = _import_first(
    [
        ("nautilus_trader.trading.strategy", "Strategy"),
        ("nautilus_trader.trading", "Strategy"),
    ]
)
StrategyConfig = _import_first(
    [
        ("nautilus_trader.config", "StrategyConfig"),
        ("nautilus_trader.trading.strategy", "StrategyConfig"),
        ("nautilus_trader.trading.config", "StrategyConfig"),
    ]
)
Data = _import_first(
    [
        ("nautilus_trader.core.data", "Data"),
        ("nautilus_trader.model.data", "Data"),
    ]
)
Bar = _import_first(
    [
        ("nautilus_trader.model.data", "Bar"),
        ("nautilus_trader.model.data.bar", "Bar"),
        ("nautilus_trader.model", "Bar"),
    ]
)
BarType = _import_first(
    [
        ("nautilus_trader.model.data", "BarType"),
        ("nautilus_trader.model.data.bar", "BarType"),
        ("nautilus_trader.model", "BarType"),
    ]
)
BarSpecification = _import_first(
    [
        ("nautilus_trader.model.data", "BarSpecification"),
        ("nautilus_trader.model.data.bar", "BarSpecification"),
        ("nautilus_trader.model", "BarSpecification"),
    ]
)
DataType = _import_first(
    [
        ("nautilus_trader.model.data", "DataType"),
        ("nautilus_trader.model.data.base", "DataType"),
        ("nautilus_trader.model", "DataType"),
    ]
)
TradeTick = _import_first(
    [
        ("nautilus_trader.model.data", "TradeTick"),
        ("nautilus_trader.model.data.tick", "TradeTick"),
        ("nautilus_trader.model", "TradeTick"),
    ]
)
QuoteTick = _import_first(
    [
        ("nautilus_trader.model.data", "QuoteTick"),
        ("nautilus_trader.model.data.tick", "QuoteTick"),
        ("nautilus_trader.model", "QuoteTick"),
    ]
)
InstrumentId = _import_first(
    [
        ("nautilus_trader.model.identifiers", "InstrumentId"),
        ("nautilus_trader.model", "InstrumentId"),
    ]
)
Symbol = _import_first(
    [
        ("nautilus_trader.model.identifiers", "Symbol"),
        ("nautilus_trader.model", "Symbol"),
    ]
)
Venue = _import_first(
    [
        ("nautilus_trader.model.identifiers", "Venue"),
        ("nautilus_trader.model", "Venue"),
    ]
)
TraderId = _import_first(
    [
        ("nautilus_trader.model.identifiers", "TraderId"),
        ("nautilus_trader.model", "TraderId"),
    ]
)
TradeId = _import_first(
    [
        ("nautilus_trader.model.identifiers", "TradeId"),
        ("nautilus_trader.model", "TradeId"),
    ]
)
Price = _import_first(
    [
        ("nautilus_trader.model.objects", "Price"),
        ("nautilus_trader.model", "Price"),
    ]
)
Quantity = _import_first(
    [
        ("nautilus_trader.model.objects", "Quantity"),
        ("nautilus_trader.model", "Quantity"),
    ]
)
Money = _import_first(
    [
        ("nautilus_trader.model.objects", "Money"),
        ("nautilus_trader.model", "Money"),
    ]
)
OrderSide = _import_first(
    [
        ("nautilus_trader.model.enums", "OrderSide"),
        ("nautilus_trader.model", "OrderSide"),
    ]
)
PositionSide = _import_first(
    [
        ("nautilus_trader.model.enums", "PositionSide"),
        ("nautilus_trader.model", "PositionSide"),
    ]
)
TimeInForce = _import_first(
    [
        ("nautilus_trader.model.enums", "TimeInForce"),
        ("nautilus_trader.model", "TimeInForce"),
    ]
)
AggressorSide = _import_first(
    [
        ("nautilus_trader.model.enums", "AggressorSide"),
        ("nautilus_trader.model", "AggressorSide"),
    ]
)
OmsType = _import_first(
    [
        ("nautilus_trader.model.enums", "OmsType"),
        ("nautilus_trader.model", "OmsType"),
    ]
)
AccountType = _import_first(
    [
        ("nautilus_trader.model.enums", "AccountType"),
        ("nautilus_trader.model", "AccountType"),
    ]
)
BookType = _import_first(
    [
        ("nautilus_trader.model.enums", "BookType"),
        ("nautilus_trader.model", "BookType"),
    ]
)
AggregationSource = _import_first(
    [
        ("nautilus_trader.model.enums", "AggregationSource"),
        ("nautilus_trader.model", "AggregationSource"),
    ]
)

try:
    PositionOpened = _import_first(
        [
            ("nautilus_trader.model.events.position", "PositionOpened"),
            ("nautilus_trader.model.events", "PositionOpened"),
        ]
    )
    PositionChanged = _import_first(
        [
            ("nautilus_trader.model.events.position", "PositionChanged"),
            ("nautilus_trader.model.events", "PositionChanged"),
        ]
    )
    PositionClosed = _import_first(
        [
            ("nautilus_trader.model.events.position", "PositionClosed"),
            ("nautilus_trader.model.events", "PositionClosed"),
        ]
    )
except ImportError:  # pragma: no cover - very old builds
    PositionOpened = PositionChanged = PositionClosed = tuple()  # type: ignore[misc, assignment]
