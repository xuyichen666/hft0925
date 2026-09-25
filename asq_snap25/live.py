"""Live Binance USD-M ASQ with frozen snap25 fair mid (ETH first).

Separate entrypoint from `asq_tick/live.py` — optimize here, then deploy
to the Tokyo server from GitHub.

Usage:
  # testnet (default)
  ASQ_INSTRUMENTS=ETHUSDT-PERP.BINANCE caffeinate -dims python -m asq_snap25

  # mainnet (Tokyo): set BINANCE_TESTNET=0 and mainnet keys in config/APIConfig.py
  BINANCE_TESTNET=0 ASQ_INSTRUMENTS=ETHUSDT-PERP.BINANCE python -m asq_snap25
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
from asq_snap25.actor import DEFAULT_MODEL_PATH, Snap25FairActor, Snap25FairConfig
from asq_tick.strategy import ASQConfig, ASQMarketMaking

# ETH-first research defaults (keep tiny until Tokyo mainnet is validated).
_CLIP_USD = 500
_MAX_INVENTORY_USD = 2500
_DEFAULT_INSTRUMENT = "ETHUSDT-PERP.BINANCE"


def _instrument_ids() -> list[str]:
    raw = os.getenv("ASQ_INSTRUMENTS") or os.getenv("ASQ_INSTRUMENT") or _DEFAULT_INSTRUMENT
    ids: list[str] = []
    for token in raw.split(","):
        iid = token.strip()
        if not iid:
            continue
        # This package's frozen model is ETH-only for now.
        symbol = iid.split(".", 1)[0].upper()
        if not symbol.startswith("ETH"):
            print(f"skip non-ETH instrument (snap25 model is ETH): {iid}")
            continue
        if iid not in ids:
            ids.append(iid)
    if not ids:
        raise RuntimeError("No ETH instruments. Set ASQ_INSTRUMENT=ETHUSDT-PERP.BINANCE")
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
            "Binance API key/secret missing. Put keys in config/APIConfig.py."
        )
    return key, secret


def _model_path() -> str:
    raw = os.getenv("ASQ_SNAP25_MODEL") or str(DEFAULT_MODEL_PATH)
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return str(path)


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


def _plain_log_to_jsonl(line: str) -> str | None:
    """Convert a Nautilus stdout line into one JSONL record for the monitor."""
    import json
    import re

    plain = re.sub(r"\x1b\[[0-9;]*m", "", line).rstrip("\r\n")
    if not plain:
        return None
    m = re.match(
        r"^(?P<ts>\d{4}-\d{2}-\d{2}T\S+)\s+\[(?P<level>[A-Z]+)\]\s+"
        r"(?P<trader>[^.]+)\.(?P<comp>[^:]+):\s*(?P<msg>.*)$",
        plain,
    )
    if not m:
        # Keep non-nautilus lines as generic records so the file is never empty.
        return json.dumps(
            {
                "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                "level": "INFO",
                "component": "stdout",
                "message": plain,
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "timestamp": m.group("ts"),
            "level": m.group("level"),
            "trader_id": m.group("trader"),
            "component": m.group("comp"),
            "message": m.group("msg"),
        },
        ensure_ascii=False,
    )


class _TeeStream:
    """Mirror Python stdout/stderr into a JSONL file (thread-safe, Windows-safe)."""

    def __init__(self, primary, log_file, lock):
        self.primary = primary
        self._f = log_file
        self._lock = lock
        self._buf = ""

    def write(self, data):
        if not isinstance(data, str):
            data = str(data)
        try:
            self.primary.write(data)
            self.primary.flush()
        except Exception:
            pass
        if not data:
            return 0
        with self._lock:
            self._buf += data
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                rec = _plain_log_to_jsonl(line)
                if rec is not None:
                    try:
                        self._f.write(rec + "\n")
                        self._f.flush()
                    except Exception:
                        pass
        return len(data)

    def flush(self):
        try:
            self.primary.flush()
        except Exception:
            pass
        try:
            self._f.flush()
        except Exception:
            pass

    def isatty(self):
        try:
            return self.primary.isatty()
        except Exception:
            return False

    def fileno(self):
        return self.primary.fileno()

    def __getattr__(self, name):
        return getattr(self.primary, name)


def _install_stdout_tee(log_path: Path) -> Path:
    """Create JSONL immediately, then tee Python stdout/stderr into it.

    Nautilus' own file logger leaves 0-byte stubs on Windows. FD pipe tees also
    fail here — so we (1) always create a non-empty file up front and (2) wrap
    sys.stdout/sys.stderr. For full Rust console capture use PowerShell Tee-Object.
    """
    import json
    import threading

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(log_path, "a", encoding="utf-8", errors="replace", buffering=1)
    boot = {
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "level": "INFO",
        "component": "live",
        "message": f"log file opened path={log_path}",
    }
    log_f.write(json.dumps(boot, ensure_ascii=False) + "\n")
    log_f.flush()

    lock = threading.Lock()
    sys.stdout = _TeeStream(sys.__stdout__, log_f, lock)
    sys.stderr = _TeeStream(sys.__stderr__, log_f, lock)
    # Always print path on the real console, even if wrapping fails later.
    sys.__stdout__.write(f"file log (tee): {log_path}\n")
    sys.__stdout__.flush()
    return log_path


def _logging_config(LoggingConfig, testnet: bool):
    """Stdout only via Nautilus; real file comes from `_install_stdout_tee`."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    env = "testnet" if testnet else "mainnet"
    directory = _log_dir()
    cfg = LoggingConfig(
        log_level="INFO",
        log_level_file=None,
        log_colors=True,
    )
    return cfg, directory / f"asq-snap25-{env}-{stamp}.jsonl"


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


def build_node(testnet: bool = True):
    _widen_binance_recv_window()
    mods = _binance_imports()
    api_key, api_secret = _keys(testnet)
    instrument_ids = _instrument_ids()
    model_path = _model_path()
    if not Path(model_path).exists():
        raise FileNotFoundError(f"snap25 model missing: {model_path}")

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
        use_reduce_only=False,
        **extra,
    )
    node_kwargs = dict(
        trader_id="ASQ-SNAP25-001",
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
        config = mods["TradingNodeConfig"](logging=logging_cfg, **node_kwargs)
    except TypeError:
        config = mods["TradingNodeConfig"](log_level="INFO", **node_kwargs)
        log_path = None
    print(f"file log: {log_path or '(stdout only)'}")
    print(f"model: {model_path}")

    node = mods["TradingNode"](config=config)
    hot_path = str(ROOT / "asq_snap25" / "live_hot.json")
    for iid in instrument_ids:
        tag = _order_tag(iid)
        actor_kwargs = dict(instrument_id=iid, model_path=model_path)
        try:
            actor_cfg = Snap25FairConfig(component_id=f"Snap25-{tag}", **actor_kwargs)
        except TypeError:
            actor_cfg = Snap25FairConfig(**actor_kwargs)
        node.trader.add_actor(Snap25FairActor(actor_cfg))
        node.trader.add_strategy(
            ASQMarketMaking(
                ASQConfig(
                    instrument_id=iid,
                    order_id_tag=f"S25{tag}",
                    notional_trade_size_usd=_CLIP_USD,
                    max_inventory_usd=_MAX_INVENTORY_USD,
                    use_fair_mid=True,
                    oms_type="HEDGING",
                    hedge_position_ids=True,
                    wait_for_cancel=True,
                    requote_ticks=3,
                    quote_interval_ms=2_000,
                    expire_time_s=15,
                    max_fair_bp=8.0,
                    min_spread_ticks=1,
                    max_spread_ticks=3,
                    max_hold_ms=8_000,
                    flatten_quote_interval_ms=500,
                    flatten_requote_ticks=2,
                    # Liquid-ETH-ish until actor get_params succeeds
                    # (old A=0.1/k=0.1 → ~900-tick spreads → always max clamp)
                    A=1.5,
                    k=80.0,
                    sigma=0.005,
                    gamma=0.01,
                    imbalance_when_weak=False,
                    hot_config_path=hot_path,
                )
            )
        )
    node.add_data_client_factory(mods["BINANCE"], mods["BinanceLiveDataClientFactory"])
    node.add_exec_client_factory(mods["BINANCE"], mods["BinanceLiveExecClientFactory"])
    node.build()
    return node


if __name__ == "__main__":
    testnet = os.getenv("BINANCE_TESTNET", "1") != "0"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    env = "testnet" if testnet else "mainnet"
    tee_path = _install_stdout_tee(_log_dir() / f"asq-snap25-{env}-{stamp}.jsonl")
    print(
        f"ASQ-snap25 live {','.join(_instrument_ids())} clip={_CLIP_USD} "
        f"testnet={testnet} model={_model_path()}"
    )
    print(f"file log (tee): {tee_path}")
    node = build_node(testnet=testnet)
    try:
        node.run()
    finally:
        node.dispose()
