"""Import shims for nautilus_trader 1.169 through 1.231."""

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
            "or install it: pip install -r asq_tick/requirements.txt"
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
DataType = _import_first(
    [
        ("nautilus_trader.model.data", "DataType"),
        ("nautilus_trader.model.data.base", "DataType"),
        ("nautilus_trader.model", "DataType"),
    ]
)
QuoteTick = _import_first(
    [
        ("nautilus_trader.model.data", "QuoteTick"),
        ("nautilus_trader.model.data.tick", "QuoteTick"),
        ("nautilus_trader.model", "QuoteTick"),
    ]
)
try:
    TradeTick = _import_first(
        [
            ("nautilus_trader.model.data", "TradeTick"),
            ("nautilus_trader.model.data.tick", "TradeTick"),
            ("nautilus_trader.model", "TradeTick"),
        ]
    )
except ImportError:  # pragma: no cover
    TradeTick = tuple()  # type: ignore[misc, assignment]
InstrumentId = _import_first(
    [
        ("nautilus_trader.model.identifiers", "InstrumentId"),
        ("nautilus_trader.model", "InstrumentId"),
    ]
)
PositionId = _import_first(
    [
        ("nautilus_trader.model.identifiers", "PositionId"),
        ("nautilus_trader.model", "PositionId"),
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
TimeInForce = _import_first(
    [
        ("nautilus_trader.model.enums", "TimeInForce"),
        ("nautilus_trader.model", "TimeInForce"),
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

try:
    OrderFilled = _import_first(
        [
            ("nautilus_trader.model.events.order", "OrderFilled"),
            ("nautilus_trader.model.events", "OrderFilled"),
        ]
    )
    OrderCancelRejected = _import_first(
        [
            ("nautilus_trader.model.events.order", "OrderCancelRejected"),
            ("nautilus_trader.model.events", "OrderCancelRejected"),
        ]
    )
    try:
        OrderRejected = _import_first(
            [
                ("nautilus_trader.model.events.order", "OrderRejected"),
                ("nautilus_trader.model.events", "OrderRejected"),
            ]
        )
    except ImportError:  # pragma: no cover
        OrderRejected = tuple()  # type: ignore[misc, assignment]
except ImportError:  # pragma: no cover
    OrderFilled = OrderCancelRejected = OrderRejected = tuple()  # type: ignore[misc, assignment]
# ==============================================================================
# OrderBookDelta / OrderBookDeltas / OrderBook
# ==============================================================================
try:
    OrderBookDelta = _import_first(
        [
            ("nautilus_trader.model.data", "OrderBookDelta"),
            ("nautilus_trader.model.data.book", "OrderBookDelta"),
            ("nautilus_trader.model.data", "OrderBookDeltas"),
            ("nautilus_trader.model.data.book", "OrderBookDeltas"),
        ]
    )
except ImportError:
    class OrderBookDelta:
        """占位类，避免 import 失败。"""
        pass

try:
    OrderBookDeltas = _import_first(
        [
            ("nautilus_trader.model.data", "OrderBookDeltas"),
            ("nautilus_trader.model.data.book", "OrderBookDeltas"),
        ]
    )
except ImportError:
    OrderBookDeltas = OrderBookDelta

try:
    OrderBook = _import_first(
        [
            ("nautilus_trader.model.book", "OrderBook"),
            ("nautilus_trader.model.orderbook", "OrderBook"),
        ]
    )
except ImportError:
    class OrderBook:
        pass