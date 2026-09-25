"""Measure whether the BTC/ETH spread is tradeable at a given sampling frequency.

Answers the only question that matters before tuning: at which horizon does the
mean-reverting edge exceed round-trip fees?
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FREQUENCIES = ["100ms", "500ms", "1s", "5s", "30s", "60s", "300s"]


def load_grid(data_dir: Path) -> pd.DataFrame:
    frames = {}
    for name, filename in (("btc", "btcusdt_perp_tob.csv"), ("eth", "ethusdt_perp_tob.csv")):
        frame = pd.read_csv(data_dir / filename)
        mid = (frame["bid"] + frame["ask"]) / 2.0
        frames[name] = pd.Series(mid.values, index=pd.to_datetime(frame["timestamp_ns"]), name=name)
    grid = pd.concat(frames.values(), axis=1).sort_index().ffill().dropna()
    return grid


def _ar1_coefficient(values: np.ndarray) -> float:
    """Closed-form OLS slope of x[t] on x[t-1]."""
    x, y = values[:-1], values[1:]
    variance = float(np.var(x))
    if variance <= 0:
        return float("nan")
    return float(np.cov(y, x)[0, 1] / variance)


def analyze(
    grid: pd.DataFrame,
    taker_bp: float,
    maker_bp: float,
    hold_s: float = 60.0,
) -> pd.DataFrame:
    rows = []
    for freq in FREQUENCIES:
        sampled = grid.resample(freq).last().ffill().dropna()
        if len(sampled) < 40:
            continue
        returns = np.log(sampled).diff().dropna()
        corr = float(returns["btc"].corr(returns["eth"]))
        beta = float(np.cov(returns["eth"], returns["btc"])[0, 1] / np.var(returns["btc"]))

        spread = np.log(sampled["eth"]) - beta * np.log(sampled["btc"])
        spread = spread - spread.mean()
        phi = _ar1_coefficient(spread.values)
        half_life = np.log(0.5) / np.log(abs(phi)) if 0 < abs(phi) < 1 else np.nan

        bar_seconds = pd.Timedelta(freq).total_seconds()
        rows.append(
            {
                "freq": freq,
                "bars": len(sampled),
                "corr": corr,
                "beta": beta,
                "spread_sd_bp": float(spread.std() * 1e4),
                "half_life_s": half_life * bar_seconds,
                "edge_2sd_bp": float(2 * spread.std() * 1e4),
            }
        )

    report = pd.DataFrame(rows)
    # Both legs pay on entry and exit; the hedge leg scales with |beta|.
    leg_factor = 2.0
    report["taker_cost_bp"] = taker_bp * 2 * leg_factor
    report["maker_cost_bp"] = maker_bp * 2 * leg_factor
    # Only the part of a dislocation that decays while we hold it is capturable.
    # The rest is unhedged risk, which is what a wide sigma at high frequency is.
    decayed = 1.0 - 0.5 ** (hold_s / report["half_life_s"])
    report[f"capture_{int(hold_s)}s_bp"] = report["edge_2sd_bp"] * decayed
    report["capture_vs_maker"] = report[f"capture_{int(hold_s)}s_bp"] / report["maker_cost_bp"]
    report["tradeable"] = report["capture_vs_maker"] > 1.0
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC/ETH spread tradeability report")
    parser.add_argument("--data-dir", default=str(Path(__file__).parent / "data"))
    parser.add_argument("--taker-bp", type=float, default=4.0)
    parser.add_argument("--maker-bp", type=float, default=2.0)
    parser.add_argument("--hold-s", type=float, default=60.0, help="assumed holding period")
    args = parser.parse_args()

    grid = load_grid(Path(args.data_dir))
    span_min = (grid.index[-1] - grid.index[0]).total_seconds() / 60
    print(f"aligned points: {len(grid):,} spanning {span_min:,.1f} min")

    report = analyze(grid, args.taker_bp, args.maker_bp, args.hold_s)
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(report.round(3).to_string(index=False))

    capture_col = f"capture_{int(args.hold_s)}s_bp"
    tradeable = report[report["tradeable"]]
    if tradeable.empty:
        best = report.loc[report["capture_vs_maker"].idxmax()]
        need = best["maker_cost_bp"] / (best[capture_col] / 2.0)
        print(
            f"\n=> Nothing clears maker fees within a {args.hold_s:.0f}s hold. "
            f"Best is {best['freq']}: captures {best[capture_col]:.1f} bp "
            f"vs {best['maker_cost_bp']:.1f} bp cost, so break-even needs a "
            f"{need:.1f}-sigma entry."
        )
        return
    best = tradeable.loc[tradeable["capture_vs_maker"].idxmax()]
    print(
        f"\n=> Best tradeable horizon: {best['freq']} "
        f"(half-life {best['half_life_s']:.0f}s, captures {best[capture_col]:.1f} bp "
        f"in {args.hold_s:.0f}s vs maker cost {best['maker_cost_bp']:.1f} bp)"
    )


if __name__ == "__main__":
    main()
