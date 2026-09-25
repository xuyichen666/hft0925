#!/usr/bin/env python3
"""Smoke tests for AS spreads, intensity fitting, and LightGBM fair mid."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from asq_tick.as_math import (
    as_ask_spread,
    as_bid_spread,
    clamp_spread,
    estimate_intensity,
    estimate_params,
    estimate_sigma,
)
from asq_tick.fair import add_features, bars_to_frame, fair_mid, fit_fair_model, predict_ret


def test_symmetric_at_flat_inventory() -> None:
    bid = as_bid_spread(0.05, 1.5, 80.0, 0.01, 0.0)
    ask = as_ask_spread(0.05, 1.5, 80.0, 0.01, 0.0)
    assert abs(bid - ask) < 1e-9, (bid, ask)
    assert bid > 0


def test_inventory_skew() -> None:
    long_bid = as_bid_spread(0.05, 1.5, 80.0, 0.01, 3.0)
    long_ask = as_ask_spread(0.05, 1.5, 80.0, 0.01, 3.0)
    # Long inventory: bid further from mid, ask closer (want to sell).
    assert long_bid > long_ask


def test_clamp() -> None:
    assert clamp_spread(0.0, 0.01, 1, 5) == 0.01
    assert clamp_spread(1.0, 0.01, 1, 5) == 0.05


def test_intensity_recovers_decay() -> None:
    """Synthetic walks that hit more often at small δ (asq get_market_speed)."""
    rng = np.random.default_rng(0)
    n = 800
    last_bid = np.full(n, 100.0)
    last_ask = np.full(n, 100.02)
    depth = rng.choice(
        [0.0, 0.01, 0.02, 0.03, 0.05, 0.08], size=n, p=[0.35, 0.25, 0.2, 0.12, 0.05, 0.03]
    )
    min_bid = last_bid - depth
    max_ask = last_ask + depth
    A, k = estimate_intensity(last_bid, last_ask, min_bid, max_ask, tick=0.01, n_levels=5)
    assert A > 0 and k > 0


def test_intensity_sparse_levels() -> None:
    """Sparse hits at far δ must still fit (skip empty levels)."""
    rng = np.random.default_rng(3)
    n = 600
    last_bid = np.full(n, 100.0)
    last_ask = np.full(n, 100.02)
    # Mostly tiny moves; rare deep walks — far levels often empty
    depth = rng.choice([0.0, 0.01, 0.02, 0.03], size=n, p=[0.55, 0.3, 0.12, 0.03])
    A, k = estimate_intensity(
        last_bid, last_ask, last_bid - depth, last_ask + depth, tick=0.01, n_levels=10
    )
    assert A > 0 and k > 0


def test_sane_default_reservation() -> None:
    """Live defaults must not produce multi-dollar spreads on ETH tick=0.01."""
    from asq_tick.as_math import ASParams

    p = ASParams(sigma=0.005, A=1.5, k=80.0, gamma=0.01)
    assert p.bid_spread(0) < 0.05  # < 5 ticks
    assert abs(p.bid_spread(0) - p.ask_spread(0)) < 1e-9


def test_params_from_random_walk() -> None:
    rng = np.random.default_rng(1)
    mid = 2500 + np.cumsum(rng.normal(0, 0.04, size=800))
    last_bid = mid - 0.01
    last_ask = mid + 0.01
    shock = np.abs(rng.choice([0.0, 0.01, 0.02, 0.05, 0.1], size=800, p=[0.3, 0.3, 0.2, 0.15, 0.05]))
    params = estimate_params(
        last_bid, last_ask, last_bid - shock, last_ask + shock, tick=0.01, bar_ms=1_000.0
    )
    assert params.sigma > 0
    assert params.A > 0
    assert params.k > 0
    assert estimate_sigma(mid, ave_time_ms=1_000.0) > 0


def test_fair_mid_scale() -> None:
    assert abs(fair_mid(2500.0, 0.0004) - 2501.0) < 1e-9


def test_features_have_target() -> None:
    n = 500
    mid = 2500 + np.linspace(0, 5, n)
    frame = bars_to_frame(
        mid - 0.01,
        mid + 0.01,
        np.full(n, 10.0),
        np.full(n, 8.0),
        mid - 0.02,
        mid + 0.02,
    )
    feat = add_features(frame, horizon_bars=60)
    assert feat["ret_fwd"].notna().sum() == n - 60
    assert feat["vol_imb"].iloc[10] > 0
    assert "GBR_1min" in feat.columns
    assert "macd" in feat.columns


def test_lgbm_uses_asq_models() -> None:
    from asq_tick.fair import _load_asq_lgbm

    fn = _load_asq_lgbm()
    assert fn.__name__ == "get_lgbm"


def test_lgbm_learns_imbalance_signal() -> None:
    rng = np.random.default_rng(2)
    n = 2000
    imb = rng.uniform(-0.8, 0.8, size=n)
    noise = rng.normal(0, 0.02, size=n)
    mid = 2500 + np.cumsum(0.08 * imb + noise)
    bid_size = 10 * (1 + imb)
    ask_size = 10 * (1 - imb)
    frame = bars_to_frame(
        mid - 0.01,
        mid + 0.01,
        np.clip(bid_size, 0.1, None),
        np.clip(ask_size, 0.1, None),
        mid - 0.03,
        mid + 0.03,
    )
    model, corr, _pred = fit_fair_model(frame, horizon_bars=60)
    pred = predict_ret(model, frame, horizon_bars=60)
    assert np.isfinite(pred)
    assert abs(pred) <= 0.0005
    assert corr == corr  # not NaN
    assert corr > 0.05


if __name__ == "__main__":
    tests = [
        test_symmetric_at_flat_inventory,
        test_inventory_skew,
        test_clamp,
        test_intensity_recovers_decay,
        test_intensity_sparse_levels,
        test_sane_default_reservation,
        test_params_from_random_walk,
        test_fair_mid_scale,
        test_features_have_target,
        test_lgbm_uses_asq_models,
        test_lgbm_learns_imbalance_signal,
    ]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print("asq_tick math smoke tests passed")
