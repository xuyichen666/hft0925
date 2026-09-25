"""Avellaneda-Stoikov market maker driven by L2 top-of-book quotes.

Port of `asq/asq.py`, `asq/ASQ_Market.py`, and `asq/aqsmodel.py:evaluation_Q_maker`:

- Both sides every quote until |net| hits Q; then only the opposite side
  (asq.py). Q is net inventory, not per-leg.
- Reservation is LightGBM fair mid (`mid * (1 + pred)`), not a trade on/off switch.
- Quotes sit at fair ± AS spread (`asq.py` / `aqsmodel`), clamped so they
  do not take. GTD lifetime matches `expire_time_s`.
- On Binance hedge, maker tags follow netting semantics so "opposite side"
  actually reduces the open leg (SELL on LONG closes LONG; not open SHORT).
  Flat book still opens BUY→LONG / SELL→SHORT like asq.py.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from asq_tick.as_math import ASParams, clamp_spread
from asq_tick.model import ModelUpdate, Prediction
from asq_tick.nt_compat import (
    DataType,
    InstrumentId,
    LogColor,
    OrderSide,
    OrderCancelRejected,
    OrderFilled,
    OrderRejected,
    PositionChanged,
    PositionClosed,
    PositionId,
    PositionOpened,
    QuoteTick,
    Strategy,
    StrategyConfig,
    TimeInForce,
)
from asq_tick.util import make_price, make_qty, qty_for_notional, quote_prices, tick_size


class ASQConfig(StrategyConfig):
    instrument_id: str
    notional_trade_size_usd: int = 50
    max_inventory_usd: int = 50
    quote_interval_ms: int = 2_000
    min_spread_ticks: int = 1
    max_spread_ticks: int = 1
    signal_threshold: float = 0.00003
    max_hold_ms: int = 5_000
    gamma: float = 0.01
    A: float = 1.5
    k: float = 80.0
    sigma: float = 0.05
    post_only: bool = True
    use_fair_mid: bool = True
    hedge_position_ids: bool = False
    wait_for_cancel: bool = False
    requote_ticks: int = 1
    imbalance_when_weak: bool = False
    flatten_quote_interval_ms: int = 400
    flatten_requote_ticks: int = 1
    spike_halt_bp: float = 12.0
    spike_window_ms: int = 1_000
    spike_halt_ms: int = 15_000
    taker_flatten: bool = False
    taker_flatten_on_spike: bool = False
    taker_offset_bp: float = 20.0
    # Cap |fair − mid| so a stale L2 fair cannot drag quotes off the BBO.
    max_fair_bp: float = 8.0
    expire_time_s: int = 1
    hot_config_path: str = ""


class ASQMarketMaking(Strategy):
    def __init__(self, config: ASQConfig):
        super().__init__(config=config)
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.params = ASParams(
            sigma=config.sigma,
            A=config.A,
            k=config.k,
            gamma=config.gamma,
        )
        self.instrument = None
        self._bid = None
        self._ask = None
        self._bid_sz = None
        self._ask_sz = None
        self._last_quote_ns = 0
        self._quoted_bid: Optional[float] = None
        self._quoted_ask: Optional[float] = None
        self._fills = 0
        self._fair_mid: Optional[float] = None
        self._pred_ret: Optional[float] = None
        self._entry_ns = 0
        self._mids: deque[tuple[int, float]] = deque(maxlen=2_000)
        self._halt_until_ns = 0
        self._gone_ids: set[str] = set()
        self._hot: dict[str, Any] = {}
        self._hot_mtime = 0
        self._hot_check_ns = 0
        # After Binance -2022 (ReduceOnly rejected), pause closing quotes so we
        # do not spam submit while local hedge legs are desynced from venue.
        self._reduce_block_until_ns = 0
        self._reduce_block_logged = False

    def on_start(self):
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return
        if hasattr(self, "subscribe_quote_ticks"):
            self.subscribe_quote_ticks(self.instrument_id)
        else:
            self.subscribe_quotes(self.instrument_id)
        for data_cls in (ModelUpdate, Prediction):
            data_type = DataType(data_cls, metadata={"instrument_id": self.instrument_id.value})
            # Custom actor data lives on the message bus; do not route to Binance.
            topic = f"data.{getattr(data_type, 'topic', data_cls.__name__)}"
            self.msgbus.subscribe(topic=topic, handler=self.handle_data)
        self._reload_hot(force=True)
        self.log.info(
            f"ASQ started {self.instrument_id} two-sided Q={self._hot_val('max_inventory_usd')} "
            f"clip={self._hot_val('notional_trade_size_usd')} expire={self._hot_val('expire_time_s')}s "
            f"hot={self.config.hot_config_path or 'off'}",
            color=LogColor.BLUE,
        )

    def on_data(self, data):
        if isinstance(data, ModelUpdate):
            self.params = ASParams(sigma=data.sigma, A=data.A, k=data.k, gamma=data.gamma)
            self.log.info(
                f"Model update sigma={data.sigma:.6f} A={data.A:.4f} k={data.k:.4f}",
                color=LogColor.BLUE,
            )
        elif isinstance(data, Prediction):
            self._fair_mid = data.prediction
            self._pred_ret = data.pred_ret

    def on_quote(self, tick: QuoteTick):
        self.on_quote_tick(tick)

    def on_quote_tick(self, tick: QuoteTick):
        if tick.instrument_id != self.instrument_id:
            return
        bid, ask, bid_sz, ask_sz = quote_prices(tick)
        if bid <= 0 or ask <= 0 or bid >= ask:
            return
        self._bid = bid
        self._ask = ask
        self._bid_sz = bid_sz
        self._ask_sz = ask_sz
        self._maybe_quote()

    def on_event(self, event):
        if isinstance(event, OrderFilled) and event.instrument_id == self.instrument_id:
            # Partial fills keep the working remainder; only drop fully done orders.
            if self._fill_is_complete(event):
                self._mark_gone(event.client_order_id)
        elif isinstance(event, OrderCancelRejected) and event.instrument_id == self.instrument_id:
            reason = str(getattr(event, "reason", ""))
            if self._order_already_gone(reason):
                self._mark_gone(event.client_order_id)
                self.log.info(
                    f"Cancel already gone {event.client_order_id} ({reason})",
                    color=LogColor.YELLOW,
                )
        elif (
            OrderRejected
            and isinstance(event, OrderRejected)
            and event.instrument_id == self.instrument_id
        ):
            reason = str(getattr(event, "reason", ""))
            self._mark_gone(getattr(event, "client_order_id", None))
            if "-2022" in reason or "ReduceOnly" in reason or "reduce only" in reason.lower():
                # Venue says there is nothing left to reduce — cool down.
                self._reduce_block_until_ns = self.clock.timestamp_ns() + 5_000_000_000
                self._quoted_bid = None
                self._quoted_ask = None
                if not self._reduce_block_logged:
                    self._reduce_block_logged = True
                    self.log.warning(
                        f"ReduceOnly rejected (-2022); pause close-side quotes 5s "
                        f"({event.client_order_id})"
                    )
            else:
                self.log.warning(f"Order rejected {event.client_order_id}: {reason}")
        if isinstance(event, (PositionOpened, PositionChanged, PositionClosed)):
            if event.instrument_id != self.instrument_id:
                return
            if getattr(event, "last_qty", None):
                self._fills += 1
                now = self.clock.timestamp_ns()
                net = self._net_qty()
                if net == 0:
                    self._entry_ns = 0
                    self._last_quote_ns = now
                    self._reduce_block_until_ns = 0
                    self._reduce_block_logged = False
                else:
                    if self._entry_ns == 0:
                        self._entry_ns = now
                    # Remainder of a partial fill is still working; stacking another
                    # reduce order is rejected as Binance -2022 in hedge mode.
                    if self._reduce_leaves(net) > 0:
                        return
                    self._last_quote_ns = 0
                    self._maybe_quote()

    def on_stop(self):
        if self.instrument is None:
            return
        self._cancel_open()
        self.close_all_positions(self.instrument_id)

    def _maybe_quote(self) -> None:
        if self.instrument is None or self._bid is None or self._ask is None:
            return
        self._reload_hot()
        now = self.clock.timestamp_ns()
        mid = (self._bid + self._ask) / 2.0
        spiked = self._update_spike(now, mid)
        halted = now < self._halt_until_ns
        inventory = self._net_qty()
        if inventory == 0:
            self._entry_ns = 0
            self._reduce_block_until_ns = 0
            self._reduce_block_logged = False
        elif self._entry_ns == 0:
            self._entry_ns = now

        # Local LONG/SHORT legs can desync from Binance hedge; -2022 means
        # "nothing left to reduce" — wait before retrying close-side quotes.
        if inventory != 0 and now < self._reduce_block_until_ns:
            return

        emergency = inventory != 0 and (
            (bool(self._hot_val("taker_flatten_on_spike")) and (spiked or halted))
            or (bool(self._hot_val("taker_flatten")) and self._should_flatten(now))
        )
        if self._has_blocking_inflight():
            return
        if emergency:
            if self._working_orders():
                self._cancel_open()
                return
            if (now - self._last_quote_ns) < 400_000_000:
                return
            self._emergency_taker_flatten(inventory)
            return
        if halted:
            if self._working_orders():
                self._cancel_open()
            self._quoted_bid = None
            self._quoted_ask = None
            return

        aged = inventory != 0 and self._should_flatten(now)
        # Maker flatten: after max_hold, only quote the closing side (no new risk).
        force_close = aged and not bool(self._hot_val("taker_flatten"))
        interval_ms = int(
            self._hot_val("flatten_quote_interval_ms")
            if (inventory != 0 and aged)
            else self._hot_val("quote_interval_ms")
        )
        interval_ns = max(interval_ms, 1) * 1_000_000
        if (now - self._last_quote_ns) < interval_ns:
            return

        qty = self._clip_qty()
        if qty <= 0:
            return
        q_clips = float(inventory / qty) if qty else 0.0
        max_clips = self._max_clips(qty)
        tick = tick_size(self.instrument)
        want_bid, want_ask = self._wanted_sides(
            q_clips, max_clips, qty, force_close=force_close, inventory=inventory
        )
        # If we only want the close side but the hedge leg is already gone, stop.
        long_q = self._side_qty(long=True)
        short_q = self._side_qty(long=False)
        if want_bid and not want_ask and short_q <= 0 and inventory >= 0:
            return
        if want_ask and not want_bid and long_q <= 0 and inventory <= 0:
            return
        bid_px, ask_px = self._quote_prices(inventory, tick, q_clips)
        open_orders = self._working_orders()
        # Hedge-mode SELL on LONG / BUY on SHORT is implicit reduce-only. A second
        # flatten that exceeds remaining inventory is rejected with -2022.
        if inventory != 0 and self._reduce_leaves(inventory) >= abs(inventory):
            if open_orders and self._same_quotes(want_bid, bid_px, want_ask, ask_px):
                return

        if open_orders:
            if self._same_quotes(want_bid, bid_px, want_ask, ask_px):
                return
            self._cancel_open()
            self._last_quote_ns = now
            # Live cancels are async; submitting in the same tick races filled/expired orders (-2011).
            if self._hot_val("wait_for_cancel"):
                return

        if want_bid:
            bid_qty = self._quote_qty(OrderSide.BUY, qty, inventory)
            bid_qty = max(bid_qty - self._side_leaves(OrderSide.BUY), Decimal("0"))
            if bid_qty > 0:
                self._submit(OrderSide.BUY, bid_px, bid_qty)
                self._quoted_bid = bid_px
            else:
                self._quoted_bid = None
        else:
            self._quoted_bid = None
        if want_ask:
            ask_qty = self._quote_qty(OrderSide.SELL, qty, inventory)
            ask_qty = max(ask_qty - self._side_leaves(OrderSide.SELL), Decimal("0"))
            if ask_qty > 0:
                self._submit(OrderSide.SELL, ask_px, ask_qty)
                self._quoted_ask = ask_px
            else:
                self._quoted_ask = None
        else:
            self._quoted_ask = None
        self._last_quote_ns = now

    def _same_quotes(self, want_bid: bool, bid_px: float, want_ask: bool, ask_px: float) -> bool:
        open_orders = self._working_orders()
        if not open_orders:
            return False
        tick = tick_size(self.instrument)
        flattening = self._net_qty() != 0
        requote = int(
            self._hot_val("flatten_requote_ticks") if flattening else self._hot_val("requote_ticks")
        )
        drift = tick * max(requote, 1)
        have_bid = have_ask = False
        for order in open_orders:
            side = getattr(order.side, "name", str(order.side))
            price = float(order.price)
            if side in {"BUY", "OrderSide.BUY"}:
                have_bid = True
                if want_bid and abs(price - bid_px) > drift + tick / 2:
                    return False
            else:
                have_ask = True
                if want_ask and abs(price - ask_px) > drift + tick / 2:
                    return False
        return have_bid == want_bid and have_ask == want_ask

    def _wanted_sides(
        self,
        q_clips: float,
        max_clips: float,
        clip: Decimal,
        *,
        force_close: bool = False,
        inventory: Decimal | None = None,
    ) -> tuple[bool, bool]:
        """asq.py: both sides until |net|>=Q, then only the opposite side.

        After max_hold (maker flatten), also quote only the closing side so
        inventory cannot keep growing while waiting for a fill.
        """
        del clip  # Q is measured in net clips, not per-leg size
        if force_close and inventory is not None and inventory != 0:
            if inventory > 0:
                return False, True
            return True, False
        if q_clips >= max_clips:
            return False, True
        if q_clips <= -max_clips:
            return True, False
        return True, True

    def _quote_qty(self, side: OrderSide, clip: Decimal, inventory: Decimal) -> Decimal:
        """Size a quote; when closing a hedge leg, do not exceed that leg."""
        long_q = self._side_qty(long=True)
        short_q = self._side_qty(long=False)
        side_name = getattr(side, "name", str(side))
        if "BUY" in side_name:
            if short_q > 0:
                # Closing SHORT — never exceed remaining short (Binance -2022).
                return min(clip, short_q, abs(inventory) if inventory < 0 else short_q)
            if inventory < 0:
                return min(clip, abs(inventory))
            return clip
        if long_q > 0:
            return min(clip, long_q, abs(inventory) if inventory > 0 else long_q)
        if inventory > 0:
            return min(clip, abs(inventory))
        return clip

    def _side_leaves(self, side: OrderSide) -> Decimal:
        want = "BUY" if "BUY" in getattr(side, "name", str(side)) else "SELL"
        total = Decimal("0")
        for order in self._working_orders():
            name = getattr(order.side, "name", str(order.side))
            if want not in name:
                continue
            total += Decimal(str(self._order_leaves(order)))
        return total

    def _should_flatten(self, now: int) -> bool:
        min_hold_ns = max(int(self._hot_val("quote_interval_ms")) * 1_000_000, 1_000_000_000)
        held = now - self._entry_ns if self._entry_ns else 0
        if held < min_hold_ns:
            return False
        return held >= int(self._hot_val("max_hold_ms")) * 1_000_000

    def _update_spike(self, now: int, mid: float) -> bool:
        if mid <= 0:
            return False
        window_ns = max(int(self._hot_val("spike_window_ms")), 1) * 1_000_000
        self._mids.append((now, mid))
        cutoff = now - window_ns
        while self._mids and self._mids[0][0] < cutoff:
            self._mids.popleft()
        if len(self._mids) < 2:
            return False
        values = [px for _, px in self._mids]
        range_bp = (max(values) - min(values)) / mid * 1e4
        jump_bp = abs(values[-1] - values[-2]) / mid * 1e4
        spiked = max(range_bp, jump_bp) >= float(self._hot_val("spike_halt_bp"))
        if not spiked:
            return False
        halt_ns = max(int(self._hot_val("spike_halt_ms")), 1) * 1_000_000
        was_halted = now < self._halt_until_ns
        self._halt_until_ns = now + halt_ns
        if not was_halted:
            self.log.warning(
                f"Spike halt range={range_bp:.1f}bp jump={jump_bp:.1f}bp "
                f"pause={self._hot_val('spike_halt_ms')}ms"
            )
        return True

    def _emergency_taker_flatten(self, inventory: Decimal) -> None:
        if self._working_orders():
            self._cancel_open()
            return
        qty = abs(inventory)
        if qty <= 0:
            return
        side = OrderSide.SELL if inventory > 0 else OrderSide.BUY
        offset = float(self._hot_val("taker_offset_bp")) / 1e4
        if inventory > 0:
            price = float(self._bid) * (1.0 - offset)
        else:
            price = float(self._ask) * (1.0 + offset)
        self.log.warning(
            f"Taker flatten {getattr(side, 'name', side)} qty={qty} px={price:.6f}"
        )
        self._submit(side, price, qty, taker=True)
        self._quoted_bid = None
        self._quoted_ask = None
        self._last_quote_ns = self.clock.timestamp_ns()

    def _imbalance_side(self) -> tuple[bool, bool]:
        if self._bid_sz is None or self._ask_sz is None:
            return False, False
        if self._bid_sz > self._ask_sz * 1.2:
            return True, False
        if self._ask_sz > self._bid_sz * 1.2:
            return False, True
        return False, False

    def _quote_prices(self, inventory: Decimal, tick: float, q_clips: float) -> tuple[float, float]:
        """asq.py + aqsmodel: reservation around fair mid, maker-clamped.

        asq.py: bid = mid - bid_spread(q), ask = mid + ask_spread(q).
        aqsmodel: use predicted fair (`mid * (1 + pred)`) and never take.
        """
        del inventory  # inventory enters through q_clips in the AS spreads
        mid = (self._bid + self._ask) / 2.0
        fair = float(self._fair_mid) if self._fair_mid and self._fair_mid > 0 else mid
        # Live safety: L2 can freeze after testnet TLS drops while bookTicker
        # keeps moving — clamp fair so quotes stay near the live BBO.
        max_bp = float(self._hot_val("max_fair_bp") or 0.0)
        if max_bp > 0 and mid > 0:
            cap = mid * max_bp / 1e4
            fair = min(max(fair, mid - cap), mid + cap)
        min_ticks = max(int(self._hot_val("min_spread_ticks")), 1)
        max_ticks = max(int(self._hot_val("max_spread_ticks")), min_ticks)
        q = float(q_clips)
        bid_spread = clamp_spread(self.params.bid_spread(q), tick, min_ticks, max_ticks)
        ask_spread = clamp_spread(self.params.ask_spread(q), tick, min_ticks, max_ticks)
        bid_px = fair - bid_spread
        ask_px = fair + ask_spread
        bid_px = min(bid_px, mid - tick, self._ask - tick)
        ask_px = max(ask_px, mid + tick, self._bid + tick)
        if bid_px >= ask_px:
            bid_px = min(self._bid, mid - tick)
            ask_px = max(self._ask, mid + tick)
        return bid_px, ask_px

    def _submit(self, side: OrderSide, price: float, qty: Decimal, *, taker: bool = False) -> None:
        quantity = make_qty(self.instrument, qty)
        if float(quantity) <= 0:
            return
        if taker:
            order = self._taker_order(side, price, quantity)
        else:
            kwargs = dict(
                instrument_id=self.instrument_id,
                order_side=side,
                price=make_price(self.instrument, price),
                quantity=quantity,
                time_in_force=TimeInForce.GTC,
                post_only=self.config.post_only,
            )
            expire_s = int(self._hot_val("expire_time_s") or 0)
            if expire_s > 0:
                if hasattr(self.clock, "utc_now"):
                    now_dt = self.clock.utc_now()
                else:
                    now_dt = datetime.fromtimestamp(
                        self.clock.timestamp_ns() / 1e9, tz=timezone.utc
                    )
                kwargs["time_in_force"] = TimeInForce.GTD
                kwargs["expire_time"] = now_dt + timedelta(seconds=expire_s)
            try:
                order = self.order_factory.limit(**kwargs)
            except TypeError:
                kwargs.pop("expire_time", None)
                kwargs["time_in_force"] = TimeInForce.GTC
                try:
                    order = self.order_factory.limit(**kwargs)
                except TypeError:
                    kwargs.pop("post_only", None)
                    order = self.order_factory.limit(**kwargs)
        position_id = self._hedge_position_id(side, reduce=taker)
        if position_id is None:
            self.submit_order(order)
        else:
            self.submit_order(order, position_id)

    def _taker_order(self, side: OrderSide, price: float, quantity):
        try:
            return self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=side,
                quantity=quantity,
            )
        except TypeError:
            pass
        kwargs = dict(
            instrument_id=self.instrument_id,
            order_side=side,
            price=make_price(self.instrument, price),
            quantity=quantity,
            time_in_force=TimeInForce.IOC,
        )
        try:
            return self.order_factory.limit(**kwargs, post_only=False)
        except TypeError:
            return self.order_factory.limit(**kwargs)

    def _hedge_position_id(self, side: OrderSide, *, reduce: bool = False):
        """Map orders onto Binance hedge legs with asq.py net-Q intent.

        asq.py labels BUY as long-* and SELL as short-*. On Binance hedge that
        opens a second leg instead of reducing, so live maker orders close an
        existing opposite leg when one is open (netting semantics). Flat book
        still opens BUY→LONG / SELL→SHORT.
        """
        if not self.config.hedge_position_ids:
            return None
        side_name = getattr(side, "name", str(side))
        is_buy = "BUY" in side_name
        long_q = self._side_qty(long=True)
        short_q = self._side_qty(long=False)
        if reduce:
            inventory = self._net_qty()
            if inventory > 0 or long_q > 0:
                suffix = "LONG"
            elif inventory < 0 or short_q > 0:
                suffix = "SHORT"
            else:
                suffix = "LONG" if is_buy else "SHORT"
        elif is_buy:
            suffix = "SHORT" if short_q > 0 else "LONG"
        else:
            suffix = "LONG" if long_q > 0 else "SHORT"
        return PositionId(f"{self.instrument_id}-{suffix}")

    def _clip_qty(self) -> Decimal:
        if self._ask is None or self._ask <= 0 or self.instrument is None:
            return Decimal("0")
        return qty_for_notional(
            self.instrument,
            self._ask,
            self._hot_val("notional_trade_size_usd"),
        )

    def _max_clips(self, clip: Decimal) -> float:
        if clip <= 0:
            return 1.0
        notional = Decimal(str(self._hot_val("max_inventory_usd")))
        return max(float(notional / (clip * Decimal(str(self._ask or 1)))), 1.0)

    def _open_positions(self) -> list:
        if hasattr(self.cache, "positions_open"):
            return list(
                self.cache.positions_open(instrument_id=self.instrument_id, strategy_id=self.id)
            )
        return [
            pos
            for pos in self.cache.positions(instrument_id=self.instrument_id, strategy_id=self.id)
            if not pos.is_closed
        ]

    def _signed_qty(self, position) -> Decimal:
        signed = getattr(position, "signed_qty", None)
        if signed is not None:
            return Decimal(str(float(signed)))
        qty = Decimal(str(float(position.quantity)))
        side = getattr(position.side, "name", str(position.side))
        return -qty if "SHORT" in side else qty

    def _net_qty(self) -> Decimal:
        return sum((self._signed_qty(pos) for pos in self._open_positions()), Decimal("0"))

    def _side_qty(self, *, long: bool) -> Decimal:
        total = Decimal("0")
        for position in self._open_positions():
            signed = self._signed_qty(position)
            if long and signed > 0:
                total += signed
            elif not long and signed < 0:
                total += -signed
        return total

    def _hot_val(self, key: str):
        if key in self._hot:
            return self._hot[key]
        return getattr(self.config, key)

    def _reload_hot(self, force: bool = False) -> None:
        path = (self.config.hot_config_path or "").strip()
        if not path:
            return
        now = self.clock.timestamp_ns()
        if not force and now - self._hot_check_ns < 1_000_000_000:
            return
        self._hot_check_ns = now
        file_path = Path(path)
        if not file_path.is_file():
            return
        mtime = file_path.stat().st_mtime_ns
        if not force and mtime == self._hot_mtime:
            return
        try:
            raw = json.loads(file_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            self.log.warning(f"Hot config skipped: {exc}")
            return
        if not isinstance(raw, dict):
            self.log.warning("Hot config skipped: root must be a JSON object")
            return
        allowed = {
            "signal_threshold",
            "quote_interval_ms",
            "max_hold_ms",
            "requote_ticks",
            "imbalance_when_weak",
            "notional_trade_size_usd",
            "max_inventory_usd",
            "wait_for_cancel",
            "spike_halt_bp",
            "spike_window_ms",
            "spike_halt_ms",
            "taker_flatten",
            "taker_flatten_on_spike",
            "taker_offset_bp",
            "min_spread_ticks",
            "max_spread_ticks",
            "flatten_quote_interval_ms",
            "flatten_requote_ticks",
            "expire_time_s",
            "max_fair_bp",
        }
        update = {k: raw[k] for k in allowed if k in raw}
        if not update:
            self._hot_mtime = mtime
            return
        self._hot.update(update)
        self._hot_mtime = mtime
        self.log.info(f"Hot config {file_path.name} {update}", color=LogColor.BLUE)

    def _order_key(self, order_id) -> str:
        return str(order_id)

    def _mark_gone(self, order_id) -> None:
        if order_id is None:
            return
        self._gone_ids.add(self._order_key(order_id))
        if len(self._gone_ids) > 4_000:
            extra = len(self._gone_ids) - 2_000
            for key in list(self._gone_ids)[:extra]:
                self._gone_ids.discard(key)

    def _order_already_gone(self, reason: str) -> bool:
        text = reason.lower()
        return "-2011" in reason or "unknown order" in text or "order does not exist" in text

    def _fill_is_complete(self, event) -> bool:
        leaves = getattr(event, "leaves_qty", None)
        if leaves is not None:
            return float(leaves) <= 0
        cid = getattr(event, "client_order_id", None)
        order = self.cache.order(cid) if cid is not None and hasattr(self.cache, "order") else None
        if order is None:
            return False
        if getattr(order, "is_closed", False) or getattr(order, "is_filled", False):
            return True
        o_leaves = getattr(order, "leaves_qty", None)
        if o_leaves is not None:
            return float(o_leaves) <= 0
        qty = getattr(order, "quantity", None)
        filled = getattr(order, "filled_qty", None)
        if qty is not None and filled is not None:
            return float(filled) + 1e-12 >= float(qty)
        return False

    def _order_leaves(self, order) -> float:
        leaves = getattr(order, "leaves_qty", None)
        if leaves is not None:
            return max(float(leaves), 0.0)
        qty = float(getattr(order, "quantity", 0) or 0)
        filled = float(getattr(order, "filled_qty", 0) or 0)
        return max(qty - filled, 0.0)

    def _reduce_leaves(self, inventory: Decimal) -> Decimal:
        if inventory == 0:
            return Decimal("0")
        want = "SELL" if inventory > 0 else "BUY"
        total = Decimal("0")
        for order in self._working_orders():
            side = getattr(order.side, "name", str(order.side))
            if want not in side:
                continue
            total += Decimal(str(self._order_leaves(order)))
        return total

    def _is_dead_order(self, order) -> bool:
        if self._order_key(getattr(order, "client_order_id", None)) in self._gone_ids:
            return True
        if getattr(order, "is_closed", False) or getattr(order, "is_filled", False):
            return True
        if self._order_leaves(order) <= 0:
            status = getattr(order.status, "name", str(order.status)).upper()
            if status in {"INITIALIZED", "SUBMITTED", "ACCEPTED", "PENDING_UPDATE", "PENDING_CANCEL", "PARTIALLY_FILLED", "PARTIAL"}:
                return False
            return True
        status = getattr(order.status, "name", str(order.status)).upper()
        return status in {"FILLED", "EXPIRED", "REJECTED", "DENIED", "CANCELED", "CANCELLED"}

    def _working_orders(self) -> list:
        if self.instrument is None:
            return []
        return [
            order
            for order in self.cache.orders_open(instrument_id=self.instrument_id, strategy_id=self.id)
            if not self._is_dead_order(order)
        ]

    def _has_blocking_inflight(self) -> bool:
        inflight = self.cache.orders_inflight(instrument_id=self.instrument_id, strategy_id=self.id)
        if not inflight:
            return False
        return any(not self._is_dead_order(order) for order in inflight)

    def _cancel_open(self) -> None:
        for order in self._working_orders():
            status = getattr(order.status, "name", str(order.status))
            if "PENDING" in status:
                continue
            if "CANCEL" in status and "REJECT" not in status:
                continue
            self.cancel_order(order=order)
