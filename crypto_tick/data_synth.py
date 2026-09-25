"""Synthetic correlated BTC/ETH perpetual trade and quote ticks.

The pair follows a log-log relationship with mean-reverting spread shocks so
the strategy has tradeable dislocations without downloading exchange data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


TICK_COLUMNS = ["timestamp_ns", "price", "size", "aggressor", "bid", "ask", "bid_size", "ask_size"]


@dataclass(frozen=True)
class SynthConfig:
    n_ticks: int = 12_000
    dt_ms: int = 50
    seed: int = 7
    btc_start: float = 65_000.0
    eth_start: float = 3_500.0
    btc_vol: float = 0.012
    idio_vol: float = 0.004
    spread_half_life_ticks: int = 80
    shock_every: int = 1_800
    shock_bp: float = 18.0
    btc_spread: float = 0.5
    eth_spread: float = 0.05


def generate_pair_ticks(config: SynthConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or SynthConfig()
    rng = np.random.default_rng(cfg.seed)

    dt = cfg.dt_ms / 1000.0
    start_ns = pd.Timestamp("2024-03-01T00:00:00Z").value
    step_ns = int(cfg.dt_ms * 1_000_000)
    ts = start_ns + np.arange(cfg.n_ticks, dtype=np.int64) * step_ns

    lam = np.log(2) / max(cfg.spread_half_life_ticks, 1)
    common = rng.normal(0.0, cfg.btc_vol * np.sqrt(dt), size=cfg.n_ticks)
    btc_log = np.log(cfg.btc_start) + np.cumsum(common)

    beta = np.log(cfg.eth_start) / np.log(cfg.btc_start)
    fair_eth_log = beta * btc_log
    spread = np.zeros(cfg.n_ticks)
    shock = np.zeros(cfg.n_ticks)
    for i in range(cfg.shock_every, cfg.n_ticks, cfg.shock_every):
        shock[i] = rng.choice([-1.0, 1.0]) * cfg.shock_bp / 10_000.0
    for i in range(1, cfg.n_ticks):
        spread[i] = spread[i - 1] * (1.0 - lam) + shock[i] + rng.normal(0.0, cfg.idio_vol * np.sqrt(dt))

    eth_log = fair_eth_log + spread
    btc = np.exp(btc_log)
    eth = np.exp(eth_log)

    btc_ticks = _to_frame(ts, btc, spread_px=cfg.btc_spread, rng=rng, size_scale=0.02)
    eth_ticks = _to_frame(ts, eth, spread_px=cfg.eth_spread, rng=rng, size_scale=0.4)
    return btc_ticks, eth_ticks


def _to_frame(
    ts: np.ndarray,
    mid: np.ndarray,
    spread_px: float,
    rng: np.random.Generator,
    size_scale: float,
) -> pd.DataFrame:
    half = spread_px / 2.0
    aggressor = np.where(rng.random(len(ts)) > 0.5, "BUYER", "SELLER")
    size = rng.uniform(size_scale, size_scale * 8.0, size=len(ts))
    bid = mid - half
    ask = mid + half
    trade_px = np.where(aggressor == "BUYER", ask, bid)
    return pd.DataFrame(
        {
            "timestamp_ns": ts,
            "price": trade_px,
            "size": size,
            "aggressor": aggressor,
            "bid": bid,
            "ask": ask,
            "bid_size": size * 3.0,
            "ask_size": size * 3.0,
        }
    )


def save_pair_csv(btc: pd.DataFrame, eth: pd.DataFrame, directory) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    btc.to_csv(directory / "btcusdt_perp_ticks.csv", index=False)
    eth.to_csv(directory / "ethusdt_perp_ticks.csv", index=False)
