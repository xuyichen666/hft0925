"""Live Binance USD-M perpetual pair trader.

Reads API keys from BINANCE_API_KEY / BINANCE_API_SECRET (or the TESTNET
equivalents). This is a research skeleton — start on testnet and keep size tiny.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_tick.model import PredictedPriceActor, PredictedPriceConfig
from crypto_tick.strategy import PairTrader, PairTraderConfig


SOURCE = "BTCUSDT-PERP.BINANCE"
TARGET = "ETHUSDT-PERP.BINANCE"


def _binance_imports():
    from nautilus_trader.adapters.binance import (
        BINANCE,
        BinanceAccountType,
        BinanceDataClientConfig,
        BinanceExecClientConfig,
        BinanceLiveDataClientFactory,
        BinanceLiveExecClientFactory,
    )
    from nautilus_trader.config import InstrumentProviderConfig, TradingNodeConfig
    from nautilus_trader.live.node import TradingNode

    return {
        "BINANCE": BINANCE,
        "BinanceAccountType": BinanceAccountType,
        "BinanceDataClientConfig": BinanceDataClientConfig,
        "BinanceExecClientConfig": BinanceExecClientConfig,
        "BinanceLiveDataClientFactory": BinanceLiveDataClientFactory,
        "BinanceLiveExecClientFactory": BinanceLiveExecClientFactory,
        "InstrumentProviderConfig": InstrumentProviderConfig,
        "TradingNodeConfig": TradingNodeConfig,
        "TradingNode": TradingNode,
    }


def build_node(testnet: bool = True):
    mods = _binance_imports()
    account_type = mods["BinanceAccountType"].USDT_FUTURES
    provider = mods["InstrumentProviderConfig"](
        load_ids=frozenset([SOURCE, TARGET]),
    )
    data_cfg = _binance_client_config(
        mods["BinanceDataClientConfig"],
        api_key=os.getenv("BINANCE_API_KEY"),
        api_secret=os.getenv("BINANCE_API_SECRET"),
        account_type=account_type,
        instrument_provider=provider,
        testnet=testnet,
    )
    exec_cfg = _binance_client_config(
        mods["BinanceExecClientConfig"],
        api_key=os.getenv("BINANCE_API_KEY"),
        api_secret=os.getenv("BINANCE_API_SECRET"),
        account_type=account_type,
        instrument_provider=provider,
        testnet=testnet,
    )
    config = mods["TradingNodeConfig"](
        trader_id="CRYPTO-PAIR-001",
        log_level="INFO",
        data_clients={mods["BINANCE"]: data_cfg},
        exec_clients={mods["BINANCE"]: exec_cfg},
        timeout_connection=30.0,
        timeout_reconciliation=10.0,
        timeout_portfolio=10.0,
        timeout_disconnection=10.0,
        timeout_post_stop=5.0,
    )
    node = mods["TradingNode"](config=config)
    node.trader.add_actor(
        PredictedPriceActor(
            PredictedPriceConfig(source_symbol=SOURCE, target_symbol=TARGET),
        )
    )
    node.trader.add_strategy(
        PairTrader(
            PairTraderConfig(
                source_symbol=SOURCE,
                target_symbol=TARGET,
                notional_trade_size_usd=200,
            )
        )
    )
    node.add_data_client_factory(mods["BINANCE"], mods["BinanceLiveDataClientFactory"])
    node.add_exec_client_factory(mods["BINANCE"], mods["BinanceLiveExecClientFactory"])
    node.build()
    return node


def _binance_client_config(cls, testnet: bool, **kwargs):
    try:
        return cls(testnet=testnet, **kwargs)
    except TypeError:
        try:
            from nautilus_trader.adapters.binance.common.enums import BinanceEnvironment

            environment = BinanceEnvironment.TESTNET if testnet else BinanceEnvironment.LIVE
            return cls(environment=environment, **kwargs)
        except Exception:
            return cls(**kwargs)


if __name__ == "__main__":
    node = build_node(testnet=os.getenv("BINANCE_TESTNET", "1") != "0")
    try:
        node.run()
    finally:
        node.dispose()
