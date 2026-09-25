"""Extract top-N depth levels into training-compatible snap25 columns.

Binance USD-M partial book only allows depth 5/10/20 (not 25). We subscribe
to 20 live and zero-pad levels 20..24 so the offline snap25 feature schema
(`N_LEVELS=25`) still works.
"""

from __future__ import annotations

from typing import Any

from model.features_snap25 import N_LEVELS

BINANCE_DEPTH_LIMITS = (5, 10, 20)
DEFAULT_LIVE_DEPTH = 20


def _as_float(x: Any) -> float:
    if x is None:
        return 0.0
    # BookLevel.size is a method returning float; price is a Price property.
    if callable(x) and not isinstance(x, type):
        try:
            x = x()
        except TypeError:
            pass
    if hasattr(x, "as_double"):
        try:
            return float(x.as_double())
        except Exception:
            pass
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _level_price_size(level: Any) -> tuple[float, float]:
    price = getattr(level, "price", None)
    # Nautilus BookLevel: `.size` is a method -> double; call it.
    size_attr = getattr(level, "size", None)
    size = size_attr() if callable(size_attr) else size_attr
    return _as_float(price), _as_float(size)


def snap25_from_book(
    book: Any,
    *,
    out_levels: int = N_LEVELS,
    take_levels: int | None = None,
) -> dict[str, float] | None:
    """Return `bid_p{i}` / `ask_q{i}` columns padded to `out_levels` (default 25).

    Column names match `model.features_snap25.SNAP_COLS` (v5). Offline CSV still
    uses `bids[i].price`; `feature_frame` renames those — live must emit v5 names.
    """
    take = int(take_levels or out_levels)
    try:
        bids = list(book.bids())[:take]
        asks = list(book.asks())[:take]
    except Exception:
        return None
    if len(bids) < 1 or len(asks) < 1:
        return None
    out: dict[str, float] = {}
    for i in range(out_levels):
        if i < len(bids):
            bp, bs = _level_price_size(bids[i])
        else:
            bp, bs = 0.0, 0.0
        if i < len(asks):
            ap, asz = _level_price_size(asks[i])
        else:
            ap, asz = 0.0, 0.0
        out[f"bid_p{i}"] = bp
        out[f"bid_q{i}"] = bs
        out[f"ask_p{i}"] = ap
        out[f"ask_q{i}"] = asz
    best_bid = out["bid_p0"]
    best_ask = out["ask_p0"]
    if best_bid <= 0 or best_ask <= 0 or best_bid >= best_ask:
        return None
    return out
