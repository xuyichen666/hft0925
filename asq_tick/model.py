"""Rolling Avellaneda-Stoikov parameter + LightGBM fair-mid actor.

Mirrors `20220617/demo/model.py`: an Actor consumes market data, fits a
model, and publishes updates for the strategy.

- (A, k, sigma) from 1-second top-of-book bars, as `asq/aqsmodel.py:get_params`
- LightGBM 1-minute mid return from `model/result/lgbm_eth_snap25.pkl`,
  published as fair mid `mid * (1 + pred)`.
- 25-level snapshot is maintained for 25-level features.
- Trade ticks fill taker buy/sell qty and volume.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

from asq_tick.as_math import ASParams, estimate_params
from asq_tick.fair import bars_to_frame, fair_mid, fit_fair_model, predict_ret
from asq_tick.nt_compat import (
    Actor,
    ActorConfig,
    BookType,
    Data,
    DataType,
    InstrumentId,
    LogColor,
    OrderBook,
    OrderBookDelta,
    QuoteTick,
)
from asq_tick.util import quote_prices, tick_size


# 25 档
N_LEVELS = 25


class ASParamConfig(ActorConfig):
    instrument_id: str
    bar_ms: int = 1_000
    lookback_bars: int = 1_800
    refit_every_bars: int = 60
    min_bars: int = 120
    gamma: float = 0.01
    n_levels: int = 10
    use_fair_mid: bool = True
    fair_horizon_bars: int = 60
    fair_min_bars: int = 480
    fair_refit_every_bars: int = 60
    fair_predict_every_bars: int = 2
    book_levels: int = N_LEVELS


class ASParamActor(Actor):
    def __init__(self, config: ASParamConfig):
        super().__init__(config=config)
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.params: Optional[ASParams] = None
        self._fair_model = None
        self._fair_corr: Optional[float] = None

        maxlen = config.lookback_bars

        # ---- TOB + trades ----
        self._last_bid: deque[float] = deque(maxlen=maxlen)
        self._last_ask: deque[float] = deque(maxlen=maxlen)
        self._last_bid_size: deque[float] = deque(maxlen=maxlen)
        self._last_ask_size: deque[float] = deque(maxlen=maxlen)
        self._min_bid: deque[float] = deque(maxlen=maxlen)
        self._max_ask: deque[float] = deque(maxlen=maxlen)
        self._buy_qty: deque[float] = deque(maxlen=maxlen)
        self._sell_qty: deque[float] = deque(maxlen=maxlen)
        self._buy_vol: deque[float] = deque(maxlen=maxlen)
        self._sell_vol: deque[float] = deque(maxlen=maxlen)

        # ---- 25 档快照 ----
        self._snapshots: deque[dict] = deque(maxlen=maxlen)

        self._bar_ms = config.bar_ms
        self._bar_key: Optional[int] = None

        # 当前 bar 的 TOB
        self._cur_last_bid = 0.0
        self._cur_last_ask = 0.0
        self._cur_last_bid_size = 0.0
        self._cur_last_ask_size = 0.0
        self._cur_min_bid = np.inf
        self._cur_max_ask = -np.inf
        self._cur_buy_qty = 0.0
        self._cur_sell_qty = 0.0
        self._cur_buy_vol = 0.0
        self._cur_sell_vol = 0.0

        # 当前 bar 的 25 档
        self._book: Optional[OrderBook] = None
        self._cur_snapshot: dict = {}

        self._bars_since_fit = 0
        self._bars_since_fair = 0
        self._tick = 0.01

        # ---- 调试计数 ----
        self._delta_count = 0
        self._bar_count = 0
        self._fair_fit_count = 0

    # ==========================================================================
    # 生命周期
    # ==========================================================================
    def on_start(self):
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return
        self._tick = tick_size(instrument)

        # 创建 OrderBook
        try:
            self._book = OrderBook(
                instrument_id=self.instrument_id,
                book_type=BookType.L2_MBP,
            )
            self.log.info("OrderBook created (L2_MBP)")
        except Exception as exc:
            self.log.error(f"Failed to create OrderBook: {exc}")
            self._book = None

        # 订阅 25 档深度
        if hasattr(self, "subscribe_order_book_deltas"):
            try:
                self.subscribe_order_book_deltas(self.instrument_id, BookType.L2_MBP)
                self.log.info("Subscribed OrderBookDelta (L2_MBP)")
            except Exception as exc:
                self.log.warning(f"subscribe_order_book_deltas L2_MBP failed: {exc}")
                try:
                    self.subscribe_order_book_deltas(self.instrument_id)
                    self.log.info("Subscribed OrderBookDelta (default)")
                except Exception as exc2:
                    self.log.error(f"subscribe_order_book_deltas failed: {exc2}")
        else:
            self.subscribe_quotes(self.instrument_id)
            self.log.info("Subscribed quotes (fallback)")

        # 订阅成交
        if hasattr(self, "subscribe_trade_ticks"):
            self.subscribe_trade_ticks(self.instrument_id)
            self.log.info("Subscribed trade ticks")
        elif hasattr(self, "subscribe_trades"):
            self.subscribe_trades(self.instrument_id)
            self.log.info("Subscribed trades")

    def on_stop(self):
        return

    # ==========================================================================
    # 订单簿
    # ==========================================================================
    def on_order_book_delta(self, data: OrderBookDelta):
        if getattr(data, "instrument_id", None) != self.instrument_id:
            return

        self._delta_count += 1
        if self._delta_count % 1000 == 0:
            self.log.info(f"on_order_book_delta #{self._delta_count}, book={'OK' if self._book else 'None'}")

        # 应用 delta 到 OrderBook
        if self._book is not None:
            try:
                self._book.apply(data)
            except Exception as exc:
                if self._delta_count % 1000 == 0:
                    self.log.warning(f"book.apply failed: {exc}")

        # 从 OrderBook 提取 25 档
        if self._book is not None:
            try:
                bids = self._book.bids()
                asks = self._book.asks()
                if bids and asks:
                    snap = {}
                    n_bids = min(len(bids), N_LEVELS)
                    n_asks = min(len(asks), N_LEVELS)
                    for i in range(n_bids):
                        snap[f"bid_p{i}"] = float(bids[i].price)
                        snap[f"bid_q{i}"] = float(bids[i].size)
                    for i in range(n_bids, N_LEVELS):
                        snap[f"bid_p{i}"] = np.nan
                        snap[f"bid_q{i}"] = np.nan
                    for i in range(n_asks):
                        snap[f"ask_p{i}"] = float(asks[i].price)
                        snap[f"ask_q{i}"] = float(asks[i].size)
                    for i in range(n_asks, N_LEVELS):
                        snap[f"ask_p{i}"] = np.nan
                        snap[f"ask_q{i}"] = np.nan
                    self._cur_snapshot = snap
            except Exception as exc:
                if self._delta_count % 1000 == 0:
                    self.log.warning(f"snapshot build failed: {exc}")

        # 更新 TOB
        bid = self._cur_snapshot.get("bid_p0", 0.0)
        ask = self._cur_snapshot.get("ask_p0", 0.0)
        bid_sz = self._cur_snapshot.get("bid_q0", 0.0)
        ask_sz = self._cur_snapshot.get("ask_q0", 0.0)

        if not (bid > 0 and ask > 0 and bid < ask):
            return

        key = int(getattr(data, "ts_event", 0) // (self._bar_ms * 1_000_000))
        if self._bar_key is None:
            self._bar_key = key
        if key != self._bar_key:
            self._flush_bar(getattr(data, "ts_init", 0))
            self._bar_key = key
            self._cur_min_bid = bid
            self._cur_max_ask = ask
        else:
            self._cur_min_bid = min(self._cur_min_bid, bid)
            self._cur_max_ask = max(self._cur_max_ask, ask)

        self._cur_last_bid = bid
        self._cur_last_ask = ask
        self._cur_last_bid_size = bid_sz
        self._cur_last_ask_size = ask_sz

    # ==========================================================================
    # 兼容旧的 quote tick
    # ==========================================================================
    def on_quote(self, tick: QuoteTick):
        self.on_quote_tick(tick)

    def on_quote_tick(self, tick: QuoteTick):
        if tick.instrument_id != self.instrument_id:
            return
        bid, ask, bid_size, ask_size = quote_prices(tick)
        if bid <= 0 or ask <= 0 or bid >= ask:
            return
        key = int(tick.ts_event // (self._bar_ms * 1_000_000))
        if self._bar_key is None:
            self._bar_key = key
        if key != self._bar_key:
            self._flush_bar(tick.ts_init)
            self._bar_key = key
            self._cur_min_bid = bid
            self._cur_max_ask = ask
        else:
            self._cur_min_bid = min(self._cur_min_bid, bid)
            self._cur_max_ask = max(self._cur_max_ask, ask)
        self._cur_last_bid = bid
        self._cur_last_ask = ask
        self._cur_last_bid_size = bid_size
        self._cur_last_ask_size = ask_size

    # ==========================================================================
    # 成交
    # ==========================================================================
    def on_trade(self, tick):
        self.on_trade_tick(tick)

    def on_trade_tick(self, tick):
        if getattr(tick, "instrument_id", None) != self.instrument_id:
            return
        qty = float(getattr(tick, "size", 0) or 0)
        px = float(getattr(tick, "price", 0) or 0)
        if qty <= 0 or px <= 0:
            return
        vol = qty * px
        side = getattr(tick, "aggressor_side", None)
        name = getattr(side, "name", str(side)).upper()
        if "BUY" in name:
            self._cur_buy_qty += qty
            self._cur_buy_vol += vol
        elif "SELL" in name:
            self._cur_sell_qty += qty
            self._cur_sell_vol += vol

    # ==========================================================================
    # Bar 结束
    # ==========================================================================
    def _flush_bar(self, ts_init: int) -> None:
        if not np.isfinite(self._cur_min_bid) or not np.isfinite(self._cur_max_ask):
            return

        self._bar_count += 1
        if self._bar_count % 60 == 0:
            self.log.info(
                f"_flush_bar #{self._bar_count}, n_bars={len(self._last_bid)}, "
                f"snapshots={len(self._snapshots)}"
            )

        # TOB
        self._last_bid.append(self._cur_last_bid)
        self._last_ask.append(self._cur_last_ask)
        self._last_bid_size.append(self._cur_last_bid_size)
        self._last_ask_size.append(self._cur_last_ask_size)
        self._min_bid.append(self._cur_min_bid)
        self._max_ask.append(self._cur_max_ask)
        self._buy_qty.append(self._cur_buy_qty)
        self._sell_qty.append(self._cur_sell_qty)
        self._buy_vol.append(self._cur_buy_vol)
        self._sell_vol.append(self._cur_sell_vol)

        # 25 档快照
        if self._cur_snapshot:
            self._snapshots.append(dict(self._cur_snapshot))
        else:
            self._snapshots.append({})

        # 清空当前 bar
        self._cur_buy_qty = 0.0
        self._cur_sell_qty = 0.0
        self._cur_buy_vol = 0.0
        self._cur_sell_vol = 0.0

        n = len(self._last_bid)
        if n >= self.config.min_bars:
            self._bars_since_fit += 1
            if self.params is None or self._bars_since_fit >= self.config.refit_every_bars:
                self._fit_as(ts_init)
                self._bars_since_fit = 0

        if self.config.use_fair_mid and n >= self.config.fair_min_bars:
            self._bars_since_fair += 1
            if self._fair_model is None or self._bars_since_fair >= self.config.fair_refit_every_bars:
                self._fit_fair(ts_init)
                self._bars_since_fair = 0
            elif self._fair_model is not None:
                every = max(int(self.config.fair_predict_every_bars), 1)
                if n % every == 0:
                    self._publish_prediction(ts_init)

    # ==========================================================================
    # 数据打包
    # ==========================================================================
    def _arrays(self):
        return (
            np.fromiter(self._last_bid, dtype=float),
            np.fromiter(self._last_ask, dtype=float),
            np.fromiter(self._last_bid_size, dtype=float),
            np.fromiter(self._last_ask_size, dtype=float),
            np.fromiter(self._min_bid, dtype=float),
            np.fromiter(self._max_ask, dtype=float),
            np.fromiter(self._buy_qty, dtype=float),
            np.fromiter(self._sell_qty, dtype=float),
            np.fromiter(self._buy_vol, dtype=float),
            np.fromiter(self._sell_vol, dtype=float),
        )

    def _snapshots_to_frame(self):
        if not self._snapshots:
            return None
        import pandas as pd
        rows = list(self._snapshots)
        cols = set()
        for r in rows:
            cols.update(r.keys())
        for r in rows:
            for c in cols:
                r.setdefault(c, np.nan)
        return pd.DataFrame(rows)

    # ==========================================================================
    # AS 参数拟合
    # ==========================================================================
    def _fit_as(self, ts_init: int) -> None:
        bid, ask, _, _, min_bid, max_ask, *_ = self._arrays()
        try:
            params = estimate_params(
                bid,
                ask,
                min_bid,
                max_ask,
                tick=self._tick,
                gamma=self.config.gamma,
                n_levels=self.config.n_levels,
                bar_ms=float(self.config.bar_ms),
            )
        except (ValueError, np.linalg.LinAlgError, RuntimeError) as exc:
            self.log.warning(f"Skip AS param fit: {exc}")
            return
        self.params = params
        self.log.info(
            f"AS params sigma={params.sigma:.6f} A={params.A:.4f} k={params.k:.4f} "
            f"bid0={params.bid_spread(0):.4f} ask0={params.ask_spread(0):.4f}",
            color=LogColor.BLUE,
        )
        self.publish_data(
            data_type=DataType(ModelUpdate, metadata={"instrument_id": self.instrument_id.value}),
            data=ModelUpdate(
                sigma=params.sigma,
                A=params.A,
                k=params.k,
                gamma=params.gamma,
                ts_init=ts_init,
            ),
        )

    # ==========================================================================
    # Fair mid
    # ==========================================================================
    def _fit_fair(self, ts_init: int) -> None:
        frame = bars_to_frame(*self._arrays())
        snap_frame = self._snapshots_to_frame()
        self.log.info(
            f"Trying fair fit: frame={len(frame)} snap_frame="
            f"{0 if snap_frame is None else len(snap_frame)}"
        )
        try:
            model, corr, pred = fit_fair_model(
                frame,
                snap_frame=snap_frame,
                horizon_bars=self.config.fair_horizon_bars,
            )
        except Exception as exc:
            self.log.warning(f"Skip fair-mid fit: {exc}")
            import traceback
            self.log.warning(traceback.format_exc())
            return
        self._fair_model = model
        self._fair_corr = corr
        self._fair_fit_count += 1
        self.log.info(
            f"Fair LGBM fit #{self._fair_fit_count} n={len(frame)} "
            f"oos_corr={corr:.4f} horizon={self.config.fair_horizon_bars}s",
            color=LogColor.BLUE,
        )
        mid = (self._cur_last_bid + self._cur_last_ask) / 2.0
        self._emit_prediction(fair_mid(mid, pred), pred, mid, ts_init)

    def _publish_prediction(self, ts_init: int) -> None:
        if self._fair_model is None:
            return
        mid = (self._cur_last_bid + self._cur_last_ask) / 2.0
        if mid <= 0:
            return
        try:
            pred = predict_ret(
                self._fair_model,
                bars_to_frame(*self._arrays()),
                snap_frame=self._snapshots_to_frame(),
                horizon_bars=self.config.fair_horizon_bars,
            )
        except Exception as exc:
            self.log.warning(f"Skip fair-mid predict: {exc}")
            return
        theo = fair_mid(mid, pred)
        self._emit_prediction(theo, pred, mid, ts_init)

    def _emit_prediction(self, theo: float, pred: float, mid: float, ts_init: int) -> None:
        self.publish_data(
            data_type=DataType(Prediction, metadata={"instrument_id": self.instrument_id.value}),
            data=Prediction(prediction=theo, pred_ret=pred, mid=mid, ts_init=ts_init),
        )


# ==============================================================================
# 自定义数据类型
# ==============================================================================
class ModelUpdate(Data):
    def __init__(self, sigma: float, A: float, k: float, gamma: float, ts_init: int):
        self.sigma = sigma
        self.A = A
        self.k = k
        self.gamma = gamma
        self._ts_event = ts_init
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init


class Prediction(Data):
    def __init__(self, prediction: float, pred_ret: float, mid: float, ts_init: int):
        self.prediction = prediction
        self.pred_ret = pred_ret
        self.mid = mid
        self._ts_event = ts_init
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init