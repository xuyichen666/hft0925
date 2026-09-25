"""Rolling OLS hedge model used by the tick pair trader.

Kept free of Nautilus imports so the math can be tested without the engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HedgeModel:
    intercept: float
    beta: float
    std_resid: float
    r2: float
    use_log: bool
    n_obs: int

    def predict(self, source_price: float) -> float:
        if source_price <= 0:
            raise ValueError("source_price must be positive")
        if self.use_log:
            return math.exp(self.intercept + self.beta * math.log(source_price))
        return self.intercept + self.beta * source_price

    def quantity_hedge_ratio(self, source_price: float, target_price: float) -> float:
        """Shares of source needed to hedge one share of target (same sign as beta)."""
        if source_price <= 0 or target_price <= 0:
            raise ValueError("prices must be positive")
        if self.use_log:
            return self.beta * (target_price / source_price)
        return self.beta


def fit_hedge_model(
    source_prices: np.ndarray,
    target_prices: np.ndarray,
    use_log: bool = True,
    fit_intercept: bool = True,
) -> HedgeModel:
    x = np.asarray(source_prices, dtype=float)
    y = np.asarray(target_prices, dtype=float)
    if x.shape != y.shape:
        raise ValueError("source and target series must have the same shape")
    if len(x) < 3:
        raise ValueError("need at least 3 observations to fit")
    if np.any(x <= 0) or np.any(y <= 0):
        raise ValueError("prices must be strictly positive")

    if use_log:
        x = np.log(x)
        y = np.log(y)

    if fit_intercept:
        design = np.column_stack([np.ones(len(x)), x])
    else:
        design = x.reshape(-1, 1)

    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coef
    resid = y - fitted
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    std = float(resid.std(ddof=1)) if len(resid) > 1 else 0.0

    if fit_intercept:
        intercept = float(coef[0])
        beta = float(coef[1])
    else:
        intercept = 0.0
        beta = float(coef[0])

    if not math.isfinite(std) or std <= 0:
        std = 1e-12

    return HedgeModel(
        intercept=intercept,
        beta=beta,
        std_resid=std,
        r2=r2,
        use_log=use_log,
        n_obs=len(x),
    )
