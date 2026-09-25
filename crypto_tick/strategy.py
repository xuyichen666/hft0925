"""Market-neutral crypto pair trader driven by trade ticks.

Changes vs the original 10-second bar IB demo:
- Trade on last trade / BBO, not 10s bars.
- Signed edge so both long and short the target actually fire.
- Decimal crypto quantities instead of integer share lots.
- Hedge via NETTING portfolio qty, not custom PositionIds.
- Rolling log-price OLS published by PredictedPriceActor.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from crypto_tick.model import ModelUpdate, Prediction
from crypto_tick.nt_compat import (
    DataType,
    InstrumentId,
    LogColor,
    OrderSide,
    PositionChanged,
    PositionClosed,
    PositionOpened,
    QuoteTick,
    Strategy,
    StrategyConfig,
    TimeInForce,
    TradeTick,
)
from crypto_tick.ols import HedgeModel
from crypto_tick.util import make_bar_type, make_price, make_qty, min_qty


class PairTraderConfig(StrategyConfig):
    source_symbol: str
    target_symbol: str
    notional_trade_size_usd: int = 10_000
    trade_width_std_dev: float = 2.0
    exit_std_frac: float = 0.25
    bar_spec: str = "50-TICK-LAST"
    signal_source: str = "trade"  # "trade" for trade ticks, "quote" for L2 top-of-book
    # "taker" crosses the spread, "maker" rests post-only at the touch,
    # "ioc_limit" sends a marketable limit capped at the model price.
    entry_style: str = "taker"
    entry_ttl_ns: int = 10_000_000_000  # cancel an unfilled resting entry after 10s
    max_hold_ns: int = 30_000_000_000  # 30 seconds
    min_order_interval_ns: int = 200_000_000  # 200 ms
    hedge_tolerance_usd: float = 25.0


class PairTrader(Strategy):
    def __init__(self, config: PairTraderConfig):
        super().__init__(config=config)
        self.source_id = InstrumentId.from_str(config.source_symbol)
        self.target_id = InstrumentId.from_str(config.target_symbol)
        self.model: Optional[HedgeModel] = None
        self.prediction: Optional[float] = None
        self._source_px: Optional[float] = None
        self._target_px: Optional[float] = None
        self._current_edge: float = 0.0
        self._current_required_edge: float = 0.0
        self._last_order_ns: int = 0
        self._open_ns: Optional[int] = None
        self._round_trips: int = 0
        self._target_bid: Optional[float] = None
        self._target_ask: Optional[float] = None
        self._entry_posted_ns: Optional[int] = None

    def on_start(self):
        self.source = self.cache.instrument(self.source_id)
        self.target = self.cache.instrument(self.target_id)
        if self.source is None or self.target is None:
            self.log.error("Instruments not loaded into cache")
            self.stop()
            return

        if self.config.signal_source == "trade":
            self._subscribe_trades(self.source_id)
            self._subscribe_trades(self.target_id)
        self._subscribe_quotes(self.source_id)
        self._subscribe_quotes(self.target_id)
        self.subscribe_bars(make_bar_type(self.source_id, self.config.bar_spec, internal=True))
        self.subscribe_bars(make_bar_type(self.target_id, self.config.bar_spec, internal=True))
        self._subscribe_custom(ModelUpdate, self.target_id)
        self._subscribe_custom(Prediction, self.target_id)

    def on_trade(self, tick: TradeTick):
        self.on_trade_tick(tick)

    def on_trade_tick(self, tick: TradeTick):
        self._on_price(tick.instrument_id, float(tick.price), tick.ts_event, "trade")

    def on_quote(self, tick: QuoteTick):
        self.on_quote_tick(tick)

    def on_quote_tick(self, tick: QuoteTick):
        bid = float(getattr(tick, "bid_price", None) or getattr(tick, "bid"))
        ask = float(getattr(tick, "ask_price", None) or getattr(tick, "ask"))
        if tick.instrument_id == self.target_id:
            self._target_bid = bid
            self._target_ask = ask
        self._on_price(tick.instrument_id, (bid + ask) / 2.0, tick.ts_event, "quote")

    def _on_price(self, instrument_id: InstrumentId, price: float, ts_event: int, source: str) -> None:
        if instrument_id == self.source_id:
            self._source_px = price
            return
        if instrument_id != self.target_id:
            return

        self._target_px = price
        if source != self.config.signal_source:
            return
        self._update_edge()
        self._check_for_entry()
        self._check_for_exit(ts_event)

    def on_data(self, data):
        if isinstance(data, ModelUpdate):
            self.model = HedgeModel(
                intercept=data.intercept,
                beta=data.beta,
                std_resid=data.std_prediction,
                r2=data.r2,
                use_log=data.use_log,
                n_obs=0,
            )
            self.log.info(
                f"Model update beta={data.beta:.6f} std={data.std_prediction:.6f} r2={data.r2:.4f}",
                color=LogColor.BLUE,
            )
        elif isinstance(data, Prediction):
            self.prediction = data.prediction
            if data.source_price:
                self._source_px = data.source_price
            self._update_edge()
            self._check_for_entry()
            self._check_for_exit(data.ts_event)

    def on_event(self, event):
        if isinstance(event, (PositionOpened, PositionChanged, PositionClosed)):
            if event.instrument_id == self.target_id:
                if isinstance(event, PositionOpened) and self._open_ns is None:
                    self._open_ns = event.ts_event
                self._hedge()
            if self._net_qty(self.target_id) == 0 and self._net_qty(self.source_id) == 0:
                if self._open_ns is not None:
                    self._round_trips += 1
                    self._open_ns = None

    def on_stop(self):
        self.close_all_positions(self.source_id)
        self.close_all_positions(self.target_id)

    def _update_edge(self) -> None:
        if self.prediction is None or self._target_px is None or self.model is None:
            self._current_edge = 0.0
            return
        self._current_edge = self.prediction - self._target_px
        scale = _residual_price_scale(self.model.use_log, self._target_px)
        self._current_required_edge = self.model.std_resid * self.config.trade_width_std_dev * scale

    def _check_for_entry(self) -> None:
        if self.prediction is None or self.model is None or self._target_px is None:
            return
        if self._net_qty(self.target_id) != 0:
            return

        resting = self.cache.orders_open(instrument_id=self.target_id, strategy_id=self.id)
        if resting:
            self._manage_resting_entry(resting)
            return
        self._entry_posted_ns = None

        if not self._can_send_order(self.target_id):
            return
        if abs(self._current_edge) <= self._current_required_edge:
            return

        if self._current_edge > 0:
            side = OrderSide.BUY
        else:
            side = OrderSide.SELL

        qty = self._target_qty()
        if qty <= 0:
            return

        self.log.info(
            f"Entry {side.name} market={self._target_px:.4f} theo={self.prediction:.4f} "
            f"qty={qty} edge={self._current_edge:.4f} required={self._current_required_edge:.4f}",
            color=LogColor.GREEN,
        )
        self._submit_target(side, qty, is_entry=True)

    def _manage_resting_entry(self, resting) -> None:
        """Pull a passive entry once it is stale or the dislocation has faded."""
        now = self.clock.timestamp_ns()
        expired = (
            self._entry_posted_ns is not None
            and (now - self._entry_posted_ns) >= self.config.entry_ttl_ns
        )
        faded = abs(self._current_edge) < (self._current_required_edge * 0.5)
        if not (expired or faded):
            return
        for order in resting:
            self.cancel_order(order=order)
        self._entry_posted_ns = None

    def _check_for_exit(self, ts_event: int) -> None:
        qty = self._net_qty(self.target_id)
        if qty == 0:
            return
        if not self._can_send_order(self.target_id):
            return

        timed_out = (
            self._open_ns is not None and (ts_event - self._open_ns) >= self.config.max_hold_ns
        )
        reverted = abs(self._current_edge) < (self._current_required_edge * self.config.exit_std_frac)
        if not (timed_out or reverted):
            return

        side = OrderSide.SELL if qty > 0 else OrderSide.BUY
        close_qty = abs(qty)
        reason = "timeout" if timed_out else "reversion"
        self.log.info(
            f"Close {reason} {side.name} qty={close_qty} edge={self._current_edge:.4f}",
            color=LogColor.CYAN,
        )
        self._submit_target(side, close_qty)

    def _hedge(self) -> None:
        if self.model is None or self._source_px is None or self._target_px is None:
            return
        if self.cache.orders_inflight(instrument_id=self.source_id, strategy_id=self.id):
            return

        target_qty = self._net_qty(self.target_id)
        ratio = self.model.quantity_hedge_ratio(self._source_px, self._target_px)
        desired_source = -float(target_qty) * ratio
        current_source = float(self._net_qty(self.source_id))
        delta = desired_source - current_source
        notional = abs(delta) * self._source_px
        if notional < self.config.hedge_tolerance_usd:
            return
        if abs(delta) < float(min_qty(self.source)):
            return

        side = OrderSide.BUY if delta > 0 else OrderSide.SELL
        qty = make_qty(self.source, abs(delta))
        if float(qty) <= 0:
            return
        self._cancel_open(self.source_id)
        order = self.order_factory.market(
            instrument_id=self.source_id,
            order_side=side,
            quantity=qty,
        )
        self.log.info(f"HEDGE {order}", color=LogColor.BLUE)
        self.submit_order(order)

    def _submit_target(self, side: OrderSide, qty: Decimal, is_entry: bool = False) -> None:
        quantity = make_qty(self.target, qty)
        if float(quantity) <= 0:
            return
        self._cancel_open(self.target_id)

        order = self._styled_entry_order(side, quantity) if is_entry else None
        if order is None:
            order = self.order_factory.market(
                instrument_id=self.target_id,
                order_side=side,
                quantity=quantity,
            )

        self._last_order_ns = self.clock.timestamp_ns()
        self.log.info(f"TARGET {order}", color=LogColor.BLUE)
        self.submit_order(order)

    def _styled_entry_order(self, side: OrderSide, quantity):
        """Build the entry order for the configured style, or None to fall back to market."""
        style = self.config.entry_style
        if style == "maker":
            return self._passive_entry_order(side, quantity)
        if style == "ioc_limit" and self.prediction is not None:
            offset = self._current_required_edge
            price = self.prediction - offset if side == OrderSide.BUY else self.prediction + offset
            return self.order_factory.limit(
                instrument_id=self.target_id,
                order_side=side,
                price=make_price(self.target, price),
                quantity=quantity,
                time_in_force=TimeInForce.IOC,
            )
        return None

    def _passive_entry_order(self, side: OrderSide, quantity):
        """Rest at the touch so the entry earns the maker fee instead of paying taker."""
        price = self._target_bid if side == OrderSide.BUY else self._target_ask
        if price is None:
            return None
        self._entry_posted_ns = self.clock.timestamp_ns()
        return self.order_factory.limit(
            instrument_id=self.target_id,
            order_side=side,
            price=make_price(self.target, price),
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )

    def _target_qty(self) -> Decimal:
        if self._target_px is None or self._target_px <= 0:
            return Decimal("0")
        notional = Decimal(self.config.notional_trade_size_usd)
        qty = notional / Decimal(str(self._target_px))
        min_target = min_qty(self.target)
        if qty < min_target:
            return Decimal("0")
        return qty

    def _net_qty(self, instrument_id: InstrumentId) -> Decimal:
        if hasattr(self.cache, "positions_open"):
            positions = self.cache.positions_open(instrument_id=instrument_id, strategy_id=self.id)
        else:
            positions = [
                pos
                for pos in self.cache.positions(instrument_id=instrument_id, strategy_id=self.id)
                if not pos.is_closed
            ]
        net = Decimal("0")
        for position in positions:
            qty = Decimal(str(position.quantity))
            if str(position.side) in {"PositionSide.SHORT", "SHORT"} or getattr(position.side, "name", "") == "SHORT":
                net -= qty
            else:
                net += qty
        return net

    def _subscribe_trades(self, instrument_id: InstrumentId) -> None:
        if hasattr(self, "subscribe_trade_ticks"):
            self.subscribe_trade_ticks(instrument_id)
        else:
            self.subscribe_trades(instrument_id)

    def _subscribe_quotes(self, instrument_id: InstrumentId) -> None:
        if hasattr(self, "subscribe_quote_ticks"):
            self.subscribe_quote_ticks(instrument_id)
        elif hasattr(self, "subscribe_quotes"):
            self.subscribe_quotes(instrument_id)

    def _subscribe_custom(self, data_cls, instrument_id: InstrumentId) -> None:
        data_type = DataType(data_cls, metadata={"instrument_id": instrument_id.value})
        try:
            self.subscribe_data(data_type, instrument_id=instrument_id)
        except TypeError:
            self.subscribe_data(data_type)

    def _can_send_order(self, instrument_id: InstrumentId) -> bool:
        if self.cache.orders_inflight(instrument_id=instrument_id, strategy_id=self.id):
            return False
        now = self.clock.timestamp_ns()
        return (now - self._last_order_ns) >= self.config.min_order_interval_ns

    def _cancel_open(self, instrument_id: InstrumentId) -> None:
        for order in self.cache.orders_open(instrument_id=instrument_id, strategy_id=self.id):
            self.cancel_order(order=order)


def _residual_price_scale(use_log: bool, target_price: float) -> float:
    """Convert a residual std into price units when the model is fit on logs."""
    if use_log:
        return max(target_price, 1e-12)
    return 1.0
