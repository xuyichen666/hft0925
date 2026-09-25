"""Backtest the ASQ market maker on L2 top-of-book.

Layout mirrors `20220617/demo/backtest.py`: engine + actor + strategy.
Data is the Tardis-style L2 dump replayed to throttled BBO quotes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asq_tick.data_l2 import load_tob
from asq_tick.fill_model import TouchFillModel
from asq_tick.instruments import load_instrument
from asq_tick.model import ASParamActor, ASParamConfig
from asq_tick.nt_compat import AccountType, BookType, OmsType, TraderId, Venue
from asq_tick.strategy import ASQConfig, ASQMarketMaking
from asq_tick.ticks import quotes_from_tob, slice_tob

DATA_DIR = Path(__file__).resolve().parent / "data"
TOB_NAMES = {
    "BTC": "btcusdt_perp_tob.csv",
    "ETH": "ethusdt_perp_tob.csv",
}


def _engine_config(log_level: str):
    try:
        from nautilus_trader.config import BacktestEngineConfig, LoggingConfig

        return BacktestEngineConfig(
            trader_id=_trader_id(),
            logging=LoggingConfig(log_level=log_level),
        )
    except TypeError:
        from nautilus_trader.config import BacktestEngineConfig

        return BacktestEngineConfig(trader_id=_trader_id())
    except ImportError:
        from nautilus_trader.backtest.config import BacktestEngineConfig

        return BacktestEngineConfig(trader_id=_trader_id())


def _trader_id():
    try:
        return TraderId("BACKTESTER-001")
    except TypeError:
        return TraderId.from_str("BACKTESTER-001")


def _build_engine(log_level: str):
    try:
        from nautilus_trader.backtest.engine import BacktestEngine
    except ImportError:
        from nautilus_trader.backtest import BacktestEngine

    engine = BacktestEngine(config=_engine_config(log_level))
    venue = Venue("BINANCE")
    usdt = _usdt()
    venue_kwargs = dict(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=usdt,
        starting_balances=[_money(5_000, usdt)],
        book_type=BookType.L1_MBP,
        fill_model=TouchFillModel(),
    )
    try:
        engine.add_venue(**venue_kwargs, trade_execution=True)
    except TypeError:
        try:
            engine.add_venue(**venue_kwargs)
        except TypeError:
            venue_kwargs.pop("book_type", None)
            engine.add_venue(**venue_kwargs)
    return engine, venue


def _usdt():
    from nautilus_trader.model.currencies import USDT

    return USDT


def _money(amount, currency):
    from nautilus_trader.model.objects import Money

    try:
        return Money(amount, currency)
    except TypeError:
        return Money.from_str(f"{amount} {currency}")


def default_data_dir() -> Path:
    local = DATA_DIR
    if (local / TOB_NAMES["ETH"]).exists() or (local / TOB_NAMES["BTC"]).exists():
        return local
    sibling = ROOT / "crypto_tick" / "data" / "full"
    if (sibling / TOB_NAMES["ETH"]).exists() or (sibling / TOB_NAMES["BTC"]).exists():
        return sibling
    return local


def _load_tob(data_dir: Path, symbol: str) -> pd.DataFrame:
    key = "BTC" if symbol.upper().startswith("BTC") else "ETH"
    path = data_dir / TOB_NAMES[key]
    if not path.exists():
        raise FileNotFoundError(
            f"Expected {path}. Convert the raw L2 dump first:\n"
            f"  python asq_tick/prepare_data.py l2 --symbol {key.lower()}"
        )
    return load_tob(path)


def run(
    symbol: str = "ETH",
    data_dir: str | None = None,
    log_level: str = "INFO",
    notional: int = 50,
    max_inventory_usd: int = 50,
    minutes: float | None = None,
    skip_minutes: float = 0.0,
    quote_interval_ms: int = 2_000,
    min_spread_ticks: int = 1,
    max_spread_ticks: int = 1,
    signal_threshold: float = 0.00003,
    max_hold_ms: int = 5_000,
    verbose: bool = False,
    use_fair_mid: bool = True,
) -> None:
    directory = Path(data_dir) if data_dir else default_data_dir()
    instrument = load_instrument(symbol)
    frame = slice_tob(_load_tob(directory, symbol), minutes=minutes, skip_minutes=skip_minutes)
    if frame.empty:
        raise ValueError(f"No top-of-book rows in {directory} for {symbol}")
    span_s = (frame.timestamp_ns.iloc[-1] - frame.timestamp_ns.iloc[0]) / 1e9
    maker = getattr(instrument, "maker_fee", None)
    taker = getattr(instrument, "taker_fee", None)
    print(
        f"ASQ L2 backtest {instrument.id} rows={len(frame):,} "
        f"span={span_s / 60:.1f} min dir={directory} "
        f"maker={maker} taker={taker} fair={use_fair_mid} "
        f"Q={max_inventory_usd} clip={notional} thr={signal_threshold} "
        f"hold={max_hold_ms}ms"
    )

    engine, venue = _build_engine(log_level=log_level)
    engine.add_instrument(instrument)
    engine.add_data(quotes_from_tob(instrument, frame))

    actor = ASParamActor(
        ASParamConfig(instrument_id=str(instrument.id), use_fair_mid=use_fair_mid)
    )
    strategy = ASQMarketMaking(
        ASQConfig(
            instrument_id=str(instrument.id),
            notional_trade_size_usd=notional,
            max_inventory_usd=max_inventory_usd,
            quote_interval_ms=quote_interval_ms,
            min_spread_ticks=min_spread_ticks,
            max_spread_ticks=max_spread_ticks,
            signal_threshold=signal_threshold,
            max_hold_ms=max_hold_ms,
            use_fair_mid=use_fair_mid,
        )
    )
    if hasattr(engine, "add_actor"):
        engine.add_actor(actor)
    else:
        engine.kernel.trader.add_actor(actor)
    engine.add_strategy(strategy)
    engine.run()
    _print_reports(engine, venue, verbose=verbose)
    engine.dispose()


def _print_reports(engine, venue, verbose: bool = False) -> None:
    reporter = getattr(engine, "trader", None) or engine
    reports = {}
    for name in ("generate_account_report", "generate_order_fills_report", "generate_positions_report"):
        fn = getattr(reporter, name, None)
        if fn is None:
            continue
        try:
            reports[name] = fn(venue) if name == "generate_account_report" else fn()
        except TypeError:
            reports[name] = fn()

    account = reports.get("generate_account_report")
    fills = reports.get("generate_order_fills_report")
    print("\n=== summary ===")
    if account is not None and not account.empty and "total" in account:
        totals = pd.to_numeric(account["total"], errors="coerce").dropna()
        if not totals.empty:
            start, end = totals.iloc[0], totals.iloc[-1]
            print(f"balance      : {start:,.2f} -> {end:,.2f} USDT ({end - start:+,.2f})")
    if fills is not None:
        print(f"fills        : {len(fills)}")
        if "ts_event" in fills.columns and len(fills) >= 2:
            ts = pd.to_numeric(fills["ts_event"], errors="coerce").dropna()
            if len(ts) >= 2:
                span_min = (ts.iloc[-1] - ts.iloc[0]) / 60e9
                if span_min > 0:
                    print(f"fill rate    : {len(fills) / span_min:.1f} / min")
        fees = _sum_money(fills.get("commissions"))
        if fees is not None:
            print(f"commissions  : {fees:,.2f} USDT")
    positions = reports.get("generate_positions_report")
    if positions is not None and not positions.empty:
        for col in ("realized_pnl", "realized_return"):
            if col in positions.columns:
                series = pd.to_numeric(positions[col].astype(str).str.split().str[0], errors="coerce")
                if series.notna().any():
                    print(f"{col:12}: {series.sum():,.4f}")
                    break
        return
    with pd.option_context("display.max_rows", 50, "display.width", 180):
        for name, report in reports.items():
            print(f"\n=== {name} ===")
            print(report)


def _print_fill_quality(fills) -> None:
    if fills is None or fills.empty:
        return
    for col in ("liquidity_side", "order_side", "side"):
        if col in fills.columns:
            counts = fills[col].astype(str).value_counts()
            print(f"{col:12}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


def _sum_money(values) -> float | None:
    if values is None:
        return None
    total = 0.0
    seen = False
    for value in values:
        items = value if isinstance(value, (list, tuple)) else [value]
        for item in items:
            amount = str(item).split(" ")[0]
            try:
                total += float(amount)
                seen = True
            except ValueError:
                continue
    return total if seen else None


def main() -> None:
    parser = argparse.ArgumentParser(description="ASQ market-making backtest on L2 top-of-book")
    parser.add_argument("--symbol", default="ETH", help="BTC or ETH (default ETH)")
    parser.add_argument("--data-dir", default=None, help="directory with *usdt_perp_tob.csv")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--notional", type=int, default=50)
    parser.add_argument("--max-inventory-usd", type=int, default=50)
    parser.add_argument("--minutes", type=float, default=None, help="replay window, default whole file")
    parser.add_argument("--skip-minutes", type=float, default=0.0)
    parser.add_argument("--quote-interval-ms", type=int, default=2_000)
    parser.add_argument("--min-spread-ticks", type=int, default=1)
    parser.add_argument("--max-spread-ticks", type=int, default=1)
    parser.add_argument("--signal-threshold", type=float, default=0.00003, help="pred_ret (0.3bp) to pick a side")
    parser.add_argument("--max-hold-ms", type=int, default=5_000, help="inventory hold before flatten (default 5s, LGBM horizon)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--no-fair",
        action="store_true",
        help="quote around live mid instead of the LightGBM fair mid",
    )
    args = parser.parse_args()
    run(
        symbol=args.symbol,
        data_dir=args.data_dir,
        log_level=args.log_level,
        notional=args.notional,
        max_inventory_usd=args.max_inventory_usd,
        minutes=args.minutes,
        skip_minutes=args.skip_minutes,
        quote_interval_ms=args.quote_interval_ms,
        min_spread_ticks=args.min_spread_ticks,
        max_spread_ticks=args.max_spread_ticks,
        signal_threshold=args.signal_threshold,
        max_hold_ms=args.max_hold_ms,
        verbose=args.verbose,
        use_fair_mid=not args.no_fair,
    )


if __name__ == "__main__":
    main()
