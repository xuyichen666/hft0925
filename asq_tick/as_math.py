"""Avellaneda-Stoikov / Guéant-Lehalle-Fernandez-Tapia quotes and intensity fit.

Aligned with `asq/aqsmodel.py` (`get_params` / `get_market_speed`):
- σ from log-mid returns, scaled by √(24·60·1000 / ave_time_ms)
- λ(δ) from hit inter-arrival times, then A·exp(-k·δ)

Hardened for sparse books (testnet / quiet hours): missing δ levels are
skipped; curve_fit falls back to log-linear OLS; never requires every level.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit


@dataclass(frozen=True)
class ASParams:
    sigma: float
    A: float
    k: float
    gamma: float = 0.01

    def bid_spread(self, q: float) -> float:
        return as_bid_spread(self.sigma, self.A, self.k, self.gamma, q)

    def ask_spread(self, q: float) -> float:
        return as_ask_spread(self.sigma, self.A, self.k, self.gamma, q)


def as_bid_spread(sigma: float, A: float, k: float, gamma: float, q: float) -> float:
    """Optimal bid distance from mid given inventory `q` (in clips)."""
    var1, scale = _reservation_parts(sigma, A, k, gamma)
    var2 = (2.0 * float(q) + 1.0) / 2.0 * scale
    return var1 + var2


def as_ask_spread(sigma: float, A: float, k: float, gamma: float, q: float) -> float:
    """Optimal ask distance from mid given inventory `q` (in clips)."""
    var1, scale = _reservation_parts(sigma, A, k, gamma)
    var2 = (2.0 * float(q) - 1.0) / 2.0 * scale
    return var1 - var2


def _reservation_parts(sigma: float, A: float, k: float, gamma: float) -> tuple[float, float]:
    A = max(float(A), 1e-12)
    k = max(float(k), 1e-12)
    gamma = max(float(gamma), 1e-12)
    sigma = max(float(sigma), 0.0)
    var1 = (1.0 / gamma) * np.log(1.0 + gamma / k)
    inside = (sigma**2) * gamma / (2.0 * k * A) * (1.0 + gamma / k) ** (1.0 + k / gamma)
    return var1, np.sqrt(max(inside, 0.0))


def estimate_sigma(mids: np.ndarray, ave_time_ms: float = 1_000.0) -> float:
    """asq/aqsmodel.get_params σ: std(Δlog mid) · √(24·60·1000 / ave_time)."""
    mids = np.asarray(mids, dtype=float)
    mids = mids[np.isfinite(mids) & (mids > 0)]
    if len(mids) < 3:
        return 0.0
    log_ret = np.diff(np.log(mids))
    log_ret = log_ret[np.isfinite(log_ret)]
    if len(log_ret) < 2:
        return 0.0
    ave = max(float(ave_time_ms), 1.0)
    return float(np.std(log_ret, ddof=0) * np.sqrt(24.0 * 60.0 * 1000.0 / ave))


def _exp_fit(x: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * np.exp(-b * x)


def _fit_exp_decay(deltas: np.ndarray, lambdas: np.ndarray, tick: float) -> tuple[float, float]:
    """Fit λ=A·exp(-k·δ). Prefer curve_fit; fall back to log-linear OLS."""
    deltas = np.asarray(deltas, dtype=float)
    lambdas = np.asarray(lambdas, dtype=float)
    mask = np.isfinite(deltas) & np.isfinite(lambdas) & (lambdas > 0) & (deltas > 0)
    deltas = deltas[mask]
    lambdas = lambdas[mask]
    if len(deltas) < 2:
        raise ValueError("intensity fit failed: need ≥2 δ levels")

    # Sort by δ ascending
    order = np.argsort(deltas)
    deltas = deltas[order]
    lambdas = lambdas[order]

    A = k = None
    try:
        p0 = (float(lambdas[0]), max(1.0 / max(tick, 1e-9), 1.0))
        params, _ = curve_fit(_exp_fit, deltas, lambdas, p0=p0, maxfev=8000)
        A, k = float(params[0]), float(params[1])
    except Exception:
        A = k = None

    if A is None or k is None or not np.isfinite(A) or not np.isfinite(k) or A <= 0 or k <= 0:
        # log λ = log A − k δ
        y = np.log(lambdas)
        x = deltas
        x_mean = float(np.mean(x))
        y_mean = float(np.mean(y))
        var_x = float(np.sum((x - x_mean) ** 2))
        if var_x <= 0:
            raise ValueError("intensity fit failed: flat δ")
        slope = float(np.sum((x - x_mean) * (y - y_mean)) / var_x)
        intercept = y_mean - slope * x_mean
        A = float(np.exp(intercept))
        k = float(-slope)
        if not np.isfinite(A) or not np.isfinite(k) or A <= 0:
            raise ValueError("intensity OLS failed")
        # Non-decaying λ → force mild positive k so spreads stay finite
        if k <= 0:
            k = max(1.0 / max(tick, 1e-9), 1e-3)

    # Sanity clamps for live ETH-ish books (avoid insane reservation)
    A = float(np.clip(A, 1e-6, 1e6))
    k = float(np.clip(k, 1e-4, 1e6))
    return A, k


def estimate_intensity(
    last_bid: np.ndarray,
    last_ask: np.ndarray,
    min_bid: np.ndarray,
    max_ask: np.ndarray,
    tick: float,
    n_levels: int = 10,
    min_hits: int = 2,
) -> tuple[float, float]:
    """asq/aqsmodel.get_market_speed with sparse-level tolerance.

    Hit at distance δ: next bar's max ask walks through `last_ask+δ`,
    or min bid through `last_bid-δ`. Inter-arrival uses bar index diff / 10.
    Levels with too few hits are skipped instead of failing the whole fit.
    """
    tick = float(tick)
    if tick <= 0 or len(last_bid) < 8:
        raise ValueError("not enough bars to estimate intensity")

    last_bid = np.asarray(last_bid, dtype=float)
    last_ask = np.asarray(last_ask, dtype=float)
    min_bid = np.asarray(min_bid, dtype=float)
    max_ask = np.asarray(max_ask, dtype=float)

    n = len(last_bid) - 1
    if n <= 0:
        raise ValueError("not enough bars to estimate intensity")

    next_min_bid = min_bid[1:]
    next_max_ask = max_ask[1:]
    bid0 = last_bid[:-1]
    ask0 = last_ask[:-1]

    n_levels = max(int(n_levels), 2)
    deltas_all = tick * np.linspace(1.0, float(n_levels), n_levels)
    xs: list[float] = []
    ys: list[float] = []

    for delta in deltas_all:
        hits = (next_max_ask > (ask0 + delta)) | (next_min_bid < (bid0 - delta))
        hit_idx = np.flatnonzero(hits)
        if len(hit_idx) < max(int(min_hits), 2):
            continue
        inter = np.diff(hit_idx.astype(float)) / 10.0
        inter = inter[np.isfinite(inter) & (inter > 0)]
        if len(inter) == 0:
            continue
        mean_dt = float(np.mean(inter))
        if not np.isfinite(mean_dt) or mean_dt <= 0:
            continue
        lam = float(delta) / mean_dt
        if np.isfinite(lam) and lam > 0:
            xs.append(float(delta))
            ys.append(lam)

    if len(xs) < 2:
        raise ValueError(f"intensity fit failed: too few hit levels ({len(xs)})")

    return _fit_exp_decay(np.asarray(xs), np.asarray(ys), tick)


def estimate_params(
    last_bid: np.ndarray,
    last_ask: np.ndarray,
    min_bid: np.ndarray,
    max_ask: np.ndarray,
    tick: float,
    gamma: float = 0.01,
    n_levels: int = 10,
    bar_ms: float = 1_000.0,
) -> ASParams:
    """asq/aqsmodel.get_params on already-aggregated 1-bar last/min/max series."""
    last_bid = np.asarray(last_bid, dtype=float)
    last_ask = np.asarray(last_ask, dtype=float)
    n = len(last_bid)
    if n < 3:
        raise ValueError("not enough bars to estimate params")
    ave_time = float(bar_ms) * max(n - 1, 1) / n
    mids = (last_bid + last_ask) / 2.0
    sigma = estimate_sigma(mids, ave_time_ms=ave_time)

    last_err: Exception | None = None
    for levels in (n_levels, min(5, n_levels), 3):
        if levels < 2:
            continue
        try:
            A, k = estimate_intensity(
                last_bid, last_ask, min_bid, max_ask, tick, n_levels=levels
            )
            return ASParams(sigma=max(sigma, 1e-8), A=A, k=k, gamma=gamma)
        except (ValueError, RuntimeError) as exc:
            last_err = exc
            continue
    raise ValueError(str(last_err) if last_err else "intensity fit failed")


def clamp_spread(spread: float, tick: float, min_ticks: int, max_ticks: int) -> float:
    lo = max(int(min_ticks), 1) * tick
    hi = max(int(max_ticks), int(min_ticks)) * tick
    if not np.isfinite(spread):
        return lo
    return float(min(max(spread, lo), hi))
