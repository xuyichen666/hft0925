"""Binance USDT-M perpetual instrument definitions for the ASQ demo."""

from __future__ import annotations

from decimal import Decimal


def load_instrument(symbol: str = "ETH"):
    """Return BTCUSDT-PERP or ETHUSDT-PERP. Default ETH, matching the original ASQ notebook."""
    key = symbol.strip().upper()
    if key.startswith("BTC"):
        return _load_pair()[0]
    if key.startswith("ETH"):
        return _load_pair()[1]
    raise ValueError(f"Unknown symbol {symbol!r}; use BTC or ETH")


def _load_pair():
    # Always use the local definitions so maker/taker fees here are what the
    # backtest actually charges. TestInstrumentProvider ships +2 bp maker.
    return _build_btc_perp(), _build_eth_perp()


def _build_btc_perp():
    from nautilus_trader.model.currencies import BTC, USDT
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.instruments import CryptoPerpetual
    from nautilus_trader.model.objects import Money, Price, Quantity

    return CryptoPerpetual(
        instrument_id=InstrumentId(symbol=Symbol("BTCUSDT-PERP"), venue=Venue("BINANCE")),
        raw_symbol=Symbol("BTCUSDT"),
        base_currency=BTC,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=1,
        price_increment=Price.from_str("0.1"),
        size_precision=3,
        size_increment=Quantity.from_str("0.001"),
        max_quantity=Quantity.from_str("1000.000"),
        min_quantity=Quantity.from_str("0.001"),
        max_notional=None,
        min_notional=Money(10.00, USDT),
        max_price=Price.from_str("809484.0"),
        min_price=Price.from_str("261.1"),
        margin_init=Decimal("0.0500"),
        margin_maint=Decimal("0.0250"),
        maker_fee=Decimal("0.0"),
        taker_fee=Decimal("0.000400"),
        ts_event=0,
        ts_init=0,
    )


def _build_eth_perp():
    from nautilus_trader.model.currencies import ETH, USDT
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.instruments import CryptoPerpetual
    from nautilus_trader.model.objects import Money, Price, Quantity

    return CryptoPerpetual(
        instrument_id=InstrumentId(symbol=Symbol("ETHUSDT-PERP"), venue=Venue("BINANCE")),
        raw_symbol=Symbol("ETHUSDT"),
        base_currency=ETH,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=2,
        price_increment=Price.from_str("0.01"),
        size_precision=3,
        size_increment=Quantity.from_str("0.001"),
        max_quantity=Quantity.from_str("10000.000"),
        min_quantity=Quantity.from_str("0.001"),
        max_notional=None,
        min_notional=Money(10.00, USDT),
        max_price=Price.from_str("152588.43"),
        min_price=Price.from_str("29.91"),
        margin_init=Decimal("0.0500"),
        margin_maint=Decimal("0.0250"),
        maker_fee=Decimal("0.0"),
        taker_fee=Decimal("0.000400"),
        ts_event=0,
        ts_init=0,
    )
