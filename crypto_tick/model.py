"""Tick-driven fair-value actor for the crypto pair.

Subscribes to trade ticks and internally aggregated tick bars. Rolling OLS is
refit on bars; predictions are published on every source trade tick.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

from crypto_tick.nt_compat import (
    Actor,
    ActorConfig,
    Bar,
    Data,
    DataType,
    InstrumentId,
    LogColor,
    QuoteTick,
    TradeTick,
)
from crypto_tick.ols import HedgeModel, fit_hedge_model
from crypto_tick.util import make_bar_type


class PredictedPriceConfig(ActorConfig):
    source_symbol: str
    target_symbol: str
    bar_spec: str = "50-TICK-LAST"
    lookback_bars: int = 400
    refit_every_bars: int = 25
    min_bars: int = 80
    use_log: bool = True
    fit_intercept: bool = True
    signal_source: str = "trade"  # "trade" for trade ticks, "quote" for L2 top-of-book


class PredictedPriceActor(Actor):
    def __init__(self, config: PredictedPriceConfig):
        super().__init__(config=config)
        self.source_id = InstrumentId.from_str(config.source_symbol)
        self.target_id = InstrumentId.from_str(config.target_symbol)
        self.source_bar_type = make_bar_type(self.source_id, config.bar_spec, internal=True)
        self.target_bar_type = make_bar_type(self.target_id, config.bar_spec, internal=True)
        self._source_closes: deque[float] = deque(maxlen=config.lookback_bars)
        self._target_closes: deque[float] = deque(maxlen=config.lookback_bars)
        self._bars_since_fit = 0
        self._last_source_px: Optional[float] = None
        self._last_target_px: Optional[float] = None
        self.model: Optional[HedgeModel] = None

    def on_start(self):
        if self.config.signal_source == "quote":
            self._subscribe_quotes(self.source_id)
            self._subscribe_quotes(self.target_id)
        else:
            self._subscribe_trades(self.source_id)
            self._subscribe_trades(self.target_id)
        self.subscribe_bars(self.source_bar_type)
        self.subscribe_bars(self.target_bar_type)

    def on_trade(self, tick: TradeTick):
        self.on_trade_tick(tick)

    def on_trade_tick(self, tick: TradeTick):
        self._on_price(tick.instrument_id, float(tick.price), tick.ts_init)

    def on_quote(self, tick: QuoteTick):
        self.on_quote_tick(tick)

    def on_quote_tick(self, tick: QuoteTick):
        bid = getattr(tick, "bid_price", None) or getattr(tick, "bid")
        ask = getattr(tick, "ask_price", None) or getattr(tick, "ask")
        self._on_price(tick.instrument_id, (float(bid) + float(ask)) / 2.0, tick.ts_init)

    def _on_price(self, instrument_id: InstrumentId, price: float, ts_init: int) -> None:
        if instrument_id == self.source_id:
            self._last_source_px = price
            self._publish_prediction(ts_init)
        elif instrument_id == self.target_id:
            self._last_target_px = price

    def _subscribe_trades(self, instrument_id: InstrumentId) -> None:
        if hasattr(self, "subscribe_trade_ticks"):
            self.subscribe_trade_ticks(instrument_id)
        else:
            self.subscribe_trades(instrument_id)

    def _subscribe_quotes(self, instrument_id: InstrumentId) -> None:
        if hasattr(self, "subscribe_quote_ticks"):
            self.subscribe_quote_ticks(instrument_id)
        else:
            self.subscribe_quotes(instrument_id)

    def on_bar(self, bar: Bar):
        close = float(bar.close)
        if bar.bar_type == self.source_bar_type:
            self._source_closes.append(close)
            self._last_source_px = close
        elif bar.bar_type == self.target_bar_type:
            self._target_closes.append(close)
            self._last_target_px = close
        else:
            return

        if bar.bar_type != self.target_bar_type:
            return

        n = min(len(self._source_closes), len(self._target_closes))
        if n < self.config.min_bars:
            return

        self._bars_since_fit += 1
        if self.model is None or self._bars_since_fit >= self.config.refit_every_bars:
            self._fit(bar.ts_init)
            self._bars_since_fit = 0

    def _fit(self, ts_init: int) -> None:
        n = min(len(self._source_closes), len(self._target_closes))
        source = np.fromiter(list(self._source_closes)[-n:], dtype=float)
        target = np.fromiter(list(self._target_closes)[-n:], dtype=float)
        try:
            model = fit_hedge_model(
                source,
                target,
                use_log=self.config.use_log,
                fit_intercept=self.config.fit_intercept,
            )
        except ValueError as exc:
            self.log.warning(f"Skip model fit: {exc}")
            return

        self.model = model
        self.log.info(
            f"Fit hedge model n={model.n_obs} beta={model.beta:.6f} "
            f"intercept={model.intercept:.6f} std={model.std_resid:.6f} r2={model.r2:.4f}",
            color=LogColor.BLUE,
        )
        update = ModelUpdate(
            intercept=model.intercept,
            beta=model.beta,
            std_prediction=model.std_resid,
            r2=model.r2,
            use_log=model.use_log,
            ts_init=ts_init,
        )
        self.publish_data(
            data_type=DataType(ModelUpdate, metadata={"instrument_id": self.target_id.value}),
            data=update,
        )
        self._publish_prediction(ts_init)

    def _publish_prediction(self, ts_init: int) -> None:
        if self.model is None or self._last_source_px is None:
            return
        pred = self.model.predict(self._last_source_px)
        prediction = Prediction(
            instrument_id=self.target_id.value,
            prediction=pred,
            source_price=self._last_source_px,
            ts_init=ts_init,
        )
        self.publish_data(
            data_type=DataType(Prediction, metadata={"instrument_id": self.target_id.value}),
            data=prediction,
        )


class ModelUpdate(Data):
    def __init__(
        self,
        intercept: float,
        beta: float,
        std_prediction: float,
        r2: float,
        use_log: bool,
        ts_init: int,
    ):
        self.intercept = intercept
        self.beta = beta
        self.std_prediction = std_prediction
        self.r2 = r2
        self.use_log = use_log
        self._ts_event = ts_init
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init


class Prediction(Data):
    def __init__(
        self,
        instrument_id: str,
        prediction: float,
        source_price: float,
        ts_init: int,
    ):
        self.instrument_id = instrument_id
        self.prediction = prediction
        self.source_price = source_price
        self._ts_event = ts_init
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init
