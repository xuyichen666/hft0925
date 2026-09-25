#!/usr/bin/env python3
"""Smoke tests for the hedge model and synthetic tick generator. No Nautilus required."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from crypto_tick.data_synth import SynthConfig, generate_pair_ticks
from crypto_tick.ols import fit_hedge_model


def test_log_log_recovery() -> None:
    rng = np.random.default_rng(0)
    source = 65_000 * np.exp(np.cumsum(rng.normal(0, 0.001, size=500)))
    beta = 1.05
    intercept = -6.2
    target = np.exp(intercept + beta * np.log(source) + rng.normal(0, 0.0005, size=500))
    model = fit_hedge_model(source, target, use_log=True, fit_intercept=True)
    assert abs(model.beta - beta) < 0.02, model
    assert abs(model.intercept - intercept) < 0.05, model
    assert model.r2 > 0.99, model
    pred = model.predict(float(source[-1]))
    assert pred > 0
    ratio = model.quantity_hedge_ratio(float(source[-1]), pred)
    assert ratio > 0


def test_linear_no_intercept() -> None:
    source = np.linspace(60_000, 70_000, 200)
    target = 0.054 * source
    model = fit_hedge_model(source, target, use_log=False, fit_intercept=False)
    assert abs(model.beta - 0.054) < 1e-6
    assert model.intercept == 0.0
    assert math.isclose(model.predict(65_000), 0.054 * 65_000, rel_tol=1e-9)


def test_synth_has_mean_reverting_gaps() -> None:
    btc, eth = generate_pair_ticks(SynthConfig(n_ticks=4_000, seed=1))
    assert len(btc) == 4_000
    assert set(btc.columns) == set(eth.columns)
    aligned = np.log(eth["price"].to_numpy()) - (
        np.log(eth["price"].iloc[0]) / np.log(btc["price"].iloc[0])
    ) * np.log(btc["price"].to_numpy())
    # Injected shocks should move the residual beyond ordinary noise.
    assert np.nanmax(np.abs(aligned - aligned.mean())) > 0.001


if __name__ == "__main__":
    test_log_log_recovery()
    test_linear_no_intercept()
    test_synth_has_mean_reverting_gaps()
    print("ols/synth smoke tests passed")
