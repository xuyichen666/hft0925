"""Live Binance USD-M perpetual ASQ market maker.

Uses keys from `config/APIConfig.py` (testnet first). Research skeleton —
keep size tiny and stay on testnet until the quotes look sane.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.APIConfig import APIConfig
from asq_tick.model import ASParamActor, ASParamConfig
from asq_tick.strategy import ASQConfig, ASQMarketMaking

# Default: one ETH clip. Cross-section later:
# ASQ_INSTRUMENTS=ETHUSDT-PERP.BINANCE,BNBUSDT-PERP.BINANCE,SOLUSDT-PERP.BINANCE
_CLIP_USD = 100
_MAX_INVENTORY_USD = 100


def _instrument_ids() -> list[str]:
    raw = os.getenv("ASQ_INSTRUMENTS") or os.getenv("ASQ_INSTRUMENT") or "ETHUSDT-PERP.BINANCE"
    ids: list[str] = []
    for token in raw.split(","):
        iid = token.strip()
        if not iid:
            continue
        symbol = iid.split(".", 1)[0].upper()
        if symbol.startswith("BTC"):
            continue
        if iid not in ids:
            ids.append(iid)
    if not ids:
        raise RuntimeError("No instruments after dropping BTC. Set ASQ_INSTRUMENT or ASQ_INSTRUMENTS.")
    return ids


def _order_tag(instrument_id: str) -> str:
    return instrument_id.split(".", 1)[0].replace("USDT-PERP", "").replace("USDC-PERP", "")


def _keys(testnet: bool) -> tuple[str, str]:
    if testnet:
        key = APIConfig.BINANCE_TESTNET_API_KEY
        secret = APIConfig.BINANCE_TESTNET_API_SECRET
    else:
        key = APIConfig.BINANCE_API_KEY
        secret = APIConfig.BINANCE_API_SECRET
    key = (key or os.getenv("BINANCE_API_KEY") or "").strip()
    secret = (secret or os.getenv("BINANCE_API_SECRET") or "").strip()
    if not key or not secret:
        raise RuntimeError(
            "Binance API key/secret missing. Put testnet keys in config/APIConfig.py "
            "(BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET)."
        )
    return key, secret


def _binance_imports():
    from nautilus_trader.adapters.binance import (
        BINANCE,
        BinanceAccountType,
        BinanceDataClientConfig,
        BinanceExecClientConfig,
        BinanceLiveDataClientFactory,
        BinanceLiveExecClientFactory,
    )
    from nautilus_trader.config import InstrumentProviderConfig, LoggingConfig, TradingNodeConfig
    from nautilus_trader.live.node import TradingNode

    return {
        "BINANCE": BINANCE,
        "BinanceAccountType": BinanceAccountType,
        "BinanceDataClientConfig": BinanceDataClientConfig,
        "BinanceExecClientConfig": BinanceExecClientConfig,
        "BinanceLiveDataClientFactory": BinanceLiveDataClientFactory,
        "BinanceLiveExecClientFactory": BinanceLiveExecClientFactory,
        "InstrumentProviderConfig": InstrumentProviderConfig,
        "LoggingConfig": LoggingConfig,
        "TradingNodeConfig": TradingNodeConfig,
        "TradingNode": TradingNode,
    }


def _widen_binance_recv_window() -> None:
    """Binance rejects signed calls if the Mac clock is >5s off (error -1021)."""
    from nautilus_trader.adapters.binance.futures.http.account import BinanceFuturesAccountHttpAPI

    orig = BinanceFuturesAccountHttpAPI.query_futures_account_info

    async def query_futures_account_info(self, recv_window: str | None = None):
        window = recv_window
        try:
            if window is None or int(window) < 60_000:
                window = "60000"
        except (TypeError, ValueError):
            window = "60000"
        return await orig(self, recv_window=window)

    BinanceFuturesAccountHttpAPI.query_futures_account_info = query_futures_account_info


def _log_dir() -> Path:
    path = ROOT / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _logging_config(LoggingConfig, testnet: bool):
    """Stdout stays human-readable; files go to logs/ as JSONL for later analysis."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    env = "testnet" if testnet else "mainnet"
    name = f"asq-{env}-{stamp}"
    directory = _log_dir()
    cfg = LoggingConfig(
        log_level="INFO",
        log_level_file="INFO",
        log_directory=str(directory),
        log_file_name=name,
        log_file_format="JSONL",
        log_file_max_size=100_000_000,
        log_file_max_backup_count=20,
    )
    return cfg, directory / f"{name}.jsonl"


def build_node(testnet: bool = True):
    _widen_binance_recv_window()
    mods = _binance_imports()
    api_key, api_secret = _keys(testnet)
    instrument_ids = _instrument_ids()
    account_type = mods["BinanceAccountType"].USDT_FUTURES
    provider = mods["InstrumentProviderConfig"](load_ids=frozenset(instrument_ids))
    extra = {}
    http = getattr(APIConfig, "BINANCE_TESTNET_HTTP", "") or os.getenv("BINANCE_TESTNET_HTTP")
    ws = getattr(APIConfig, "BINANCE_TESTNET_WS", "") or os.getenv("BINANCE_TESTNET_WS")
    if testnet and http:
        extra["base_url_http"] = http
    if testnet and ws:
        extra["base_url_ws"] = ws
    data_cfg = _binance_client_config(
        mods["BinanceDataClientConfig"],
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret,
        account_type=account_type,
        instrument_provider=provider,
        **extra,
    )
    exec_cfg = _binance_client_config(
        mods["BinanceExecClientConfig"],
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret,
        account_type=account_type,
        instrument_provider=provider,
        recv_window_ms=60_000,
        # Testnet futures often defaults to Hedge Mode; Binance rejects reduceOnly there.
        use_reduce_only=False,
        **extra,
    )
    node_kwargs = dict(
        trader_id="ASQ-MM-001",
        data_clients={mods["BINANCE"]: data_cfg},
        exec_clients={mods["BINANCE"]: exec_cfg},
        timeout_connection=30.0,
        timeout_reconciliation=10.0,
        timeout_portfolio=10.0,
        timeout_disconnection=10.0,
        timeout_post_stop=5.0,
    )
    logging_cfg, log_path = _logging_config(mods["LoggingConfig"], testnet)
    try:
        config = mods["TradingNodeConfig"](
            logging=logging_cfg,
            **node_kwargs,
        )
    except TypeError:
        config = mods["TradingNodeConfig"](log_level="INFO", **node_kwargs)
        log_path = None
    print(f"file log: {log_path or '(stdout only)'}")
    node = mods["TradingNode"](config=config)
    hot_path = str(ROOT / "asq_tick" / "live_hot.json")
    for iid in instrument_ids:
        tag = _order_tag(iid)
        actor_kwargs = dict(instrument_id=iid)
        try:
            actor_cfg = ASParamConfig(component_id=f"ASParam-{tag}", **actor_kwargs)
        except TypeError:
            actor_cfg = ASParamConfig(**actor_kwargs)
        node.trader.add_actor(ASParamActor(actor_cfg))
        node.trader.add_strategy(
            ASQMarketMaking(
                ASQConfig(
                    instrument_id=iid,
                    order_id_tag=tag,
                    notional_trade_size_usd=_CLIP_USD,
                    max_inventory_usd=_MAX_INVENTORY_USD,
                    use_fair_mid=True,
                    oms_type="HEDGING",
                    hedge_position_ids=True,
                    wait_for_cancel=True,
                    requote_ticks=1,
                    quote_interval_ms=1_000,
                    expire_time_s=1,
                    min_spread_ticks=1,
                    max_spread_ticks=8,
                    imbalance_when_weak=False,
                    hot_config_path=hot_path,
                )
            )
        )
    node.add_data_client_factory(mods["BINANCE"], mods["BinanceLiveDataClientFactory"])
    node.add_exec_client_factory(mods["BINANCE"], mods["BinanceLiveExecClientFactory"])
    node.build()
    return node


def _binance_client_config(cls, testnet: bool, **kwargs):
    from nautilus_trader.adapters.binance.common.enums import BinanceEnvironment

    environment = BinanceEnvironment.TESTNET if testnet else BinanceEnvironment.LIVE
    try:
        return cls(environment=environment, **kwargs)
    except TypeError:
        try:
            return cls(testnet=testnet, **kwargs)
        except TypeError:
            kwargs.pop("environment", None)
            return cls(**kwargs)


if __name__ == "__main__":
    testnet = os.getenv("BINANCE_TESTNET", "1") != "0"
    print(
        f"ASQ live {','.join(_instrument_ids())} clip={_CLIP_USD} "
        f"testnet={testnet} keys=config/APIConfig.py"
    )
    node = build_node(testnet=testnet)
    try:
        node.run()
    finally:
        node.dispose()