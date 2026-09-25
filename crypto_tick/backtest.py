"""Backtest the crypto tick pair trader on synthetic or downloaded ticks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_tick.data_l2 import load_tob
from crypto_tick.data_synth import SynthConfig, generate_pair_ticks
from crypto_tick.instruments import load_btc_eth_perps
from crypto_tick.model import PredictedPriceActor, PredictedPriceConfig
from crypto_tick.nt_compat import AccountType, BookType, OmsType, TraderId, Venue
from crypto_tick.strategy import PairTrader, PairTraderConfig
from crypto_tick.ticks import frames_to_nautilus, quotes_from_tob


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
        starting_balances=[_money(100_000, usdt)],
        book_type=BookType.L1_MBP,
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


def _load_csv_pair(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    btc_path = data_dir / "btcusdt_perp_ticks.csv"
    eth_path = data_dir / "ethusdt_perp_ticks.csv"
    if not btc_path.exists() or not eth_path.exists():
        raise FileNotFoundError(
            f"Expected {btc_path.name} and {eth_path.name} in {data_dir}. "
            "Run with --source synth or download ticks first."
        )
    return pd.read_csv(btc_path), pd.read_csv(eth_path)


_BAR_UNIT_SECONDS = {
    "MILLISECOND": 0.001,
    "SECOND": 1.0,
    "MINUTE": 60.0,
    "HOUR": 3600.0,
    "DAY": 86400.0,
}


def _warn_if_too_short(bar_spec: str, min_bars: int, span_s: float) -> None:
    """A window longer than the data trades nothing, which is easy to mistake for a bug."""
    parts = bar_spec.split("-")
    if len(parts) < 2 or parts[1] not in _BAR_UNIT_SECONDS:
        return
    try:
        warmup_s = int(parts[0]) * _BAR_UNIT_SECONDS[parts[1]] * min_bars
    except ValueError:
        return
    if warmup_s < span_s:
        return
    print(
        f"WARNING: {bar_spec} x {min_bars} min_bars needs {warmup_s / 60:,.0f} min of warmup "
        f"but the data spans only {span_s / 60:,.0f} min, so nothing will trade. "
        "Lower --min-bars or use a longer sample."
    )


def _load_tob_pair(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    btc_path = data_dir / "btcusdt_perp_tob.csv"
    eth_path = data_dir / "ethusdt_perp_tob.csv"
    if not btc_path.exists() or not eth_path.exists():
        raise FileNotFoundError(
            f"Expected {btc_path.name} and {eth_path.name} in {data_dir}. "
            "Convert the raw L2 dumps first: python crypto_tick/prepare_data.py l2 ..."
        )
    return load_tob(btc_path), load_tob(eth_path)


DATA_DIR = Path(__file__).resolve().parent / "data"

# The L2 preset follows analyze.py: the regression window must be much longer
# than the ~25 min spread half-life, and the hold at least as long as it.
PRESETS = {
    "l2": {
        "data_dir": DATA_DIR / "full",
        "signal_source": "quote",
        "bar_spec": "30-SECOND-MID",
        "lookback_bars": 1440,
        "refit_every_bars": 120,
        "min_bars": 480,
        "entry_style": "maker",
        "trade_width_std_dev": 2.0,
        "max_hold_s": 7200.0,
    },
    "ticks": {
        "data_dir": DATA_DIR,
        "signal_source": "trade",
        "bar_spec": "50-TICK-LAST",
        "lookback_bars": 400,
        "refit_every_bars": 25,
        "min_bars": 80,
        "entry_style": "taker",
        "trade_width_std_dev": 2.0,
        "max_hold_s": 30.0,
    },
}


def preset_for(source: str) -> dict:
    return dict(PRESETS["l2" if source == "l2" else "ticks"])


def run(
    source: str = "l2",
    data_dir: str | None = None,
    log_level: str = "INFO",
    notional: int = 5_000,
    bar_spec: str | None = None,
    verbose: bool = False,
    entry_style: str | None = None,
    trade_width_std_dev: float | None = None,
    max_hold_s: float | None = None,
    lookback_bars: int | None = None,
    refit_every_bars: int | None = None,
    min_bars: int | None = None,
) -> None:
    preset = preset_for(source)
    directory = Path(data_dir) if data_dir else preset["data_dir"]
    signal_source = preset["signal_source"]
    spec = bar_spec or preset["bar_spec"]
    entry_style = entry_style or preset["entry_style"]
    trade_width_std_dev = trade_width_std_dev or preset["trade_width_std_dev"]
    max_hold_s = max_hold_s or preset["max_hold_s"]
    lookback_bars = lookback_bars or preset["lookback_bars"]
    refit_every_bars = refit_every_bars or preset["refit_every_bars"]
    min_bars = min_bars or preset["min_bars"]

    btc, eth = load_btc_eth_perps()
    print(
        f"source={source} dir={directory} bars={spec} lookback={lookback_bars} "
        f"entry={entry_style} {trade_width_std_dev}sigma hold<={max_hold_s:.0f}s"
    )

    engine, venue = _build_engine(log_level=log_level)
    engine.add_instrument(btc)
    engine.add_instrument(eth)

    if source == "l2":
        btc_df, eth_df = _load_tob_pair(directory)
        span_s = (eth_df.timestamp_ns.iloc[-1] - eth_df.timestamp_ns.iloc[0]) / 1e9
        print(
            f"Loaded top-of-book rows: BTC={len(btc_df):,} ETH={len(eth_df):,} "
            f"spanning {span_s / 60:,.0f} min"
        )
        _warn_if_too_short(spec, min_bars, span_s)
        engine.add_data(quotes_from_tob(btc, btc_df))
        engine.add_data(quotes_from_tob(eth, eth_df))
    else:
        if source == "synth":
            btc_df, eth_df = generate_pair_ticks(SynthConfig())
        else:
            btc_df, eth_df = _load_csv_pair(directory)
        btc_trades, btc_quotes = frames_to_nautilus(btc, btc_df)
        eth_trades, eth_quotes = frames_to_nautilus(eth, eth_df)
        engine.add_data(btc_quotes + eth_quotes)
        engine.add_data(btc_trades + eth_trades)

    actor = PredictedPriceActor(
        PredictedPriceConfig(
            source_symbol=str(btc.id),
            target_symbol=str(eth.id),
            bar_spec=spec,
            signal_source=signal_source,
            lookback_bars=lookback_bars,
            refit_every_bars=refit_every_bars,
            min_bars=min_bars,
        )
    )
    strategy = PairTrader(
        PairTraderConfig(
            source_symbol=str(btc.id),
            target_symbol=str(eth.id),
            notional_trade_size_usd=notional,
            bar_spec=spec,
            signal_source=signal_source,
            entry_style=entry_style,
            trade_width_std_dev=trade_width_std_dev,
            max_hold_ns=int(max_hold_s * 1_000_000_000),
        )
    )
    if hasattr(engine, "add_actor"):
        engine.add_actor(actor)
    else:
        engine.kernel.trader.add_actor(actor)
    engine.add_strategy(strategy)

    engine.run()
    _print_reports(engine, venue, verbose=verbose, notional=notional, target_id=str(eth.id))
    engine.dispose()


def _print_reports(engine, venue, verbose: bool = False, notional: int = 0, target_id: str = "") -> None:
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

    _print_summary(reports, notional=notional, target_id=target_id)
    if not verbose:
        return
    with pd.option_context("display.max_rows", 50, "display.width", 180):
        for name, report in reports.items():
            print(f"\n=== {name} ===")
            print(report)


def _print_summary(reports: dict[str, pd.DataFrame], notional: int = 0, target_id: str = "") -> None:
    account = reports.get("generate_account_report")
    fills = reports.get("generate_order_fills_report")
    positions = reports.get("generate_positions_report")

    print("\n=== summary ===")
    net = fees = None
    if account is not None and not account.empty and "total" in account:
        totals = pd.to_numeric(account["total"], errors="coerce").dropna()
        if not totals.empty:
            start, end = totals.iloc[0], totals.iloc[-1]
            net = end - start
            print(f"balance      : {start:,.2f} -> {end:,.2f} USDT ({net:+,.2f})")
    if fills is not None:
        print(f"fills        : {len(fills)}")
        fees = _sum_money(fills.get("commissions"))
        if fees is not None:
            print(f"commissions  : {fees:,.2f} USDT")
    if net is not None and fees is not None:
        print(f"gross pnl    : {net + fees:+,.2f} USDT (before fees)")

    trips = _count_round_trips(positions, target_id)
    if trips:
        print(f"round trips  : {trips}")
        if net is not None and fees is not None and notional:
            gross_bp = (net + fees) / trips / notional * 1e4
            fee_bp = fees / trips / notional * 1e4
            print(f"per round trip: gross {gross_bp:+.2f} bp vs fees {fee_bp:.2f} bp of target notional")


def _count_round_trips(positions: pd.DataFrame | None, target_id: str) -> int:
    """One snapshot row is written per closed position lifecycle on the target leg."""
    if positions is None or positions.empty or "is_snapshot" not in positions:
        return 0
    on_target = positions["instrument_id"].astype(str) == target_id
    return int((on_target & positions["is_snapshot"].astype(bool)).sum())


def _sum_money(values) -> float | None:
    """Sum Nautilus Money strings, which may be scalars or lists per row."""
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
    parser = argparse.ArgumentParser(description="Crypto tick pair-trading backtest")
    parser.add_argument("--source", choices=["l2", "synth", "csv"], default="l2")
    parser.add_argument("--data-dir", default=None, help="defaults to the preset for --source")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--notional", type=int, default=5_000)
    parser.add_argument("--verbose", action="store_true", help="print full Nautilus reports")
    # Everything below defaults to the per-source preset when omitted.
    parser.add_argument("--bar-spec", default=None)
    parser.add_argument("--entry-style", choices=["taker", "maker", "ioc_limit"], default=None)
    parser.add_argument("--std-dev", type=float, default=None, help="entry threshold in sigmas")
    parser.add_argument("--max-hold-s", type=float, default=None)
    parser.add_argument("--lookback-bars", type=int, default=None)
    parser.add_argument("--refit-every", type=int, default=None)
    parser.add_argument("--min-bars", type=int, default=None)
    args = parser.parse_args()
    run(
        source=args.source,
        data_dir=args.data_dir,
        log_level=args.log_level,
        notional=args.notional,
        bar_spec=args.bar_spec,
        verbose=args.verbose,
        entry_style=args.entry_style,
        trade_width_std_dev=args.std_dev,
        max_hold_s=args.max_hold_s,
        lookback_bars=args.lookback_bars,
        refit_every_bars=args.refit_every,
        min_bars=args.min_bars,
    )


if __name__ == "__main__":
    main()
