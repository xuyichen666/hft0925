"""Fill model that can complete maker quotes at the live BBO.

L1 quote replay has no queue: a bid resting on the best bid does not match
anything in the book, so Nautilus logs "no fills from book" unless the fill
model injects opposite-side size. `BestPriceFillModel` does that at the
quoted price (maker, not a cross).

Two-sided quotes would then round-trip on the same tick; the strategy quotes
only one side at a time.
"""

from nautilus_trader.backtest.models.fill import BestPriceFillModel


class TouchFillModel(BestPriceFillModel):
    def fill_limit_inside_spread(self) -> bool:
        return True
