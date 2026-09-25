"""Frozen snap25 LightGBM fair-mid actor + rolling AS (A,k,σ) params.

- Fair: `model/result/lgbm_eth_snap25.pkl` (no online refit)
- Features: depth-25 book + trades via `model.features_snap25`
- Publishes the same `Prediction` / `ModelUpdate` types as `asq_tick`,
  so `asq_tick.strategy.ASQMarketMaking` can be reused unchanged.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

from asq_tick.as_math import ASParams, estimate_params, estimate_sigma
from asq_tick.model import ModelUpdate, Prediction
from asq_tick.nt_compat import (
    Actor,
    ActorConfig,
    BookType,
    DataType,
    InstrumentId,
    LogColor,
)
from asq_tick.util import quote_prices, tick_size
from asq_snap25.book import DEFAULT_LIVE_DEPTH, snap25_from_book
from model.features_snap25 import (
    N_LEVELS,
    SNAP_COLS,
    Y_CLIP,
    _add_moment_and_gap,
    aggregate_1s_features,
    aggregate_trades_1s,
    calculate_features,
    merge_trade_features,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = ROOT / "model" / "result" / "lgbm_eth_snap25.pkl"


class Snap25FairConfig(ActorConfig):
    instrument_id: str
    model_path: str = str(DEFAULT_MODEL_PATH)
    bar_ms: int = 1_000
    # Binance futures valid partial depths: 5/10/20 (25 is rejected with -4021).
    book_depth: int = DEFAULT_LIVE_DEPTH
    feature_levels: int = N_LEVELS  # model schema still expects 25 cols (pad)
    history_bars: int = 400
    min_bars: int = 120
    fair_min_bars: int = 360  # aqsmodel uses up to 5min trade rolling (300) + buffer
    fair_predict_every_bars: int = 1
    as_refit_every_bars: int = 60
    gamma: float = 0.01  # aqsmodel / asq.py default
    n_levels_as: int = 10
    # Liquid-ETH-ish reservation until get_params succeeds.
    # (A=0.1,k=0.1 → ~900-tick spreads that always clamp to max_spread.)
    default_sigma: float = 0.005
    default_A: float = 1.5
    default_k: float = 80.0
    use_fair_mid: bool = True


class Snap25FairActor(Actor):
    def __init__(self, config: Snap25FairConfig):
        super().__init__(config=config)
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self._model = None
        self._features: list[str] = []
        self._y_clip = Y_CLIP
        self._predict_secs = 30
        self._signal_threshold = 0.0
        self._tick = 0.01

        self._snap_hist: deque[dict[str, float]] = deque(maxlen=config.history_bars)
        self._trade_rows: list[dict[str, float]] = []
        self._cur_trades: list[dict[str, Any]] = []
        self._bar_key: Optional[int] = None
        self._bars = 0
        self._bars_since_as = 0
        self._last_bid = 0.0
        self._last_ask = 0.0
        self._mid_hist: deque[float] = deque(maxlen=config.history_bars)
        # AS bars from bookTicker-style quotes (asq/aqsmodel groupby last/min/max)
        maxlen = config.history_bars
        self._as_last_bid: deque[float] = deque(maxlen=maxlen)
        self._as_last_ask: deque[float] = deque(maxlen=maxlen)
        self._as_min_bid: deque[float] = deque(maxlen=maxlen)
        self._as_max_ask: deque[float] = deque(maxlen=maxlen)
        self._as_bar_key: Optional[int] = None
        self._cur_last_bid = 0.0
        self._cur_last_ask = 0.0
        self._cur_min_bid = np.inf
        self._cur_max_ask = -np.inf
        self._as_params = ASParams(
            sigma=config.default_sigma,
            A=config.default_A,
            k=config.default_k,
            gamma=config.gamma,
        )
        self._warmup_logged = False
        self._predict_fail_logged_ns = 0
        self._pred_log_ns = 0
        self._stale_book_log_ns = 0
        # Max |L2 mid − bookTicker mid| before we treat depth as stale (bps).
        self._stale_book_bp = 8.0
        self._stale_book_log_ns = 0

    def on_start(self):
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return
        self._tick = tick_size(instrument)
        self._load_model()

        depth = int(self.config.book_depth)
        if depth not in (5, 10, 20):
            self.log.warning(f"book_depth={depth} invalid for Binance; using {DEFAULT_LIVE_DEPTH}")
            depth = DEFAULT_LIVE_DEPTH
        # Prefer 1s book snapshots (matches offline downsample). Fall back to deltas.
        try:
            self.subscribe_order_book_at_interval(
                self.instrument_id,
                book_type=BookType.L2_MBP,
                depth=depth,
                interval_ms=int(self.config.bar_ms),
            )
            self.log.info(
                f"Subscribed order_book_at_interval depth={depth} "
                f"(pad→{self.config.feature_levels}) ms={self.config.bar_ms}"
            )
        except Exception as exc:
            self.log.warning(f"at_interval failed ({exc}); using deltas depth={depth}")
            self.subscribe_order_book_deltas(
                self.instrument_id,
                book_type=BookType.L2_MBP,
                depth=depth,
            )

        if hasattr(self, "subscribe_trade_ticks"):
            self.subscribe_trade_ticks(self.instrument_id)
        elif hasattr(self, "subscribe_trades"):
            self.subscribe_trades(self.instrument_id)

        # asq uses bookTicker ticks to build 1s last/min/max for get_params
        if hasattr(self, "subscribe_quote_ticks"):
            self.subscribe_quote_ticks(self.instrument_id)
        elif hasattr(self, "subscribe_quotes"):
            self.subscribe_quotes(self.instrument_id)

        self.log.info(
            f"Snap25 fair ready model={self.config.model_path} "
            f"feats={len(self._features)} horizon={self._predict_secs}s "
            f"thr={self._signal_threshold:.6f} warmup>={self.config.fair_min_bars}s "
            f"AS defaults A={self.config.default_A} k={self.config.default_k}",
            color=LogColor.BLUE,
        )

    def _load_model(self) -> None:
        path = Path(self.config.model_path)
        if not path.exists():
            raise FileNotFoundError(f"snap25 model not found: {path}")
        bundle = joblib.load(path)
        self._model = bundle["model"] if isinstance(bundle, dict) else bundle
        meta = bundle.get("meta", {}) if isinstance(bundle, dict) else {}
        self._features = list(meta.get("features") or [])
        if not self._features:
            raise RuntimeError(f"model meta missing features: {path}")
        self._y_clip = float(meta.get("y_clip", Y_CLIP))
        self._predict_secs = int(meta.get("predict_secs", 30))
        self._signal_threshold = float(meta.get("signal_threshold", 0.0) or 0.0)

    def on_trade(self, tick):
        self.on_trade_tick(tick)

    def on_trade_tick(self, tick):
        if getattr(tick, "instrument_id", None) != self.instrument_id:
            return
        qty = float(getattr(tick, "size", 0) or 0)
        px = float(getattr(tick, "price", 0) or 0)
        if qty <= 0 or px <= 0:
            return
        side = getattr(tick, "aggressor_side", None)
        name = getattr(side, "name", str(side)).upper()
        if "BUY" in name:
            side_s = "buy"
        elif "SELL" in name:
            side_s = "sell"
        else:
            return
        ts = int(getattr(tick, "ts_event", 0) or 0)
        # Nautilus ts is ns; training trades CSV used microseconds.
        ts_us = ts // 1_000 if ts > 10**15 else ts
        self._cur_trades.append(
            {"timestamp": ts_us, "side": side_s, "price": px, "amount": qty}
        )

    def on_quote(self, tick):
        self.on_quote_tick(tick)

    def on_quote_tick(self, tick):
        """Accumulate 1s bp/ap last + bp.min + ap.max like asq/aqsmodel.get_params."""
        if getattr(tick, "instrument_id", None) != self.instrument_id:
            return
        bid, ask, _, _ = quote_prices(tick)
        if bid <= 0 or ask <= 0 or bid >= ask:
            return
        ts = int(getattr(tick, "ts_event", 0) or getattr(tick, "ts_init", 0) or 0)
        key = int(ts // (self.config.bar_ms * 1_000_000))
        if self._as_bar_key is None:
            self._as_bar_key = key
            self._cur_min_bid = bid
            self._cur_max_ask = ask
        elif key != self._as_bar_key:
            self._flush_as_bar(ts)
            self._as_bar_key = key
            self._cur_min_bid = bid
            self._cur_max_ask = ask
        else:
            self._cur_min_bid = min(self._cur_min_bid, bid)
            self._cur_max_ask = max(self._cur_max_ask, ask)
        self._cur_last_bid = bid
        self._cur_last_ask = ask

    def _flush_as_bar(self, ts_init: int) -> None:
        if not np.isfinite(self._cur_min_bid) or not np.isfinite(self._cur_max_ask):
            return
        if self._cur_last_bid <= 0 or self._cur_last_ask <= 0:
            return
        self._as_last_bid.append(float(self._cur_last_bid))
        self._as_last_ask.append(float(self._cur_last_ask))
        self._as_min_bid.append(float(self._cur_min_bid))
        self._as_max_ask.append(float(self._cur_max_ask))
        n = len(self._as_last_bid)
        if n >= self.config.min_bars:
            self._bars_since_as += 1
            if self._bars_since_as >= self.config.as_refit_every_bars or n == self.config.min_bars:
                self._fit_as(ts_init)
                self._bars_since_as = 0

    def _update_as_extremes_from_tob(self, bid: float, ask: float, ts_ns: int) -> None:
        """Also fold depth updates into AS extremes when quotes are sparse (testnet)."""
        if bid <= 0 or ask <= 0 or bid >= ask:
            return
        key = int(ts_ns // (self.config.bar_ms * 1_000_000)) if ts_ns else None
        if key is None:
            return
        if self._as_bar_key is None:
            self._as_bar_key = key
            self._cur_min_bid = bid
            self._cur_max_ask = ask
            self._cur_last_bid = bid
            self._cur_last_ask = ask
            return
        if key != self._as_bar_key:
            self._flush_as_bar(ts_ns)
            self._as_bar_key = key
            self._cur_min_bid = bid
            self._cur_max_ask = ask
        else:
            self._cur_min_bid = min(self._cur_min_bid, bid)
            self._cur_max_ask = max(self._cur_max_ask, ask)
        self._cur_last_bid = bid
        self._cur_last_ask = ask

    def on_order_book(self, book):
        if getattr(book, "instrument_id", None) != self.instrument_id:
            return
        ts = int(getattr(book, "ts_event", 0) or getattr(book, "ts_init", 0) or 0)
        self._ingest_book(book, ts)

    def on_order_book_deltas(self, deltas):
        # Managed book path: pull latest book from cache when deltas arrive.
        book = None
        if hasattr(self.cache, "order_book"):
            try:
                book = self.cache.order_book(self.instrument_id)
            except Exception:
                book = None
        if book is None:
            return
        ts = int(getattr(deltas, "ts_event", 0) or 0)
        key = int(ts // (self.config.bar_ms * 1_000_000)) if ts else None
        if key is None:
            return
        bid = float(book.best_bid_price or 0) if hasattr(book, "best_bid_price") else 0.0
        ask = float(book.best_ask_price or 0) if hasattr(book, "best_ask_price") else 0.0
        try:
            bid = float(getattr(bid, "as_double", lambda: bid)())
            ask = float(getattr(ask, "as_double", lambda: ask)())
        except Exception:
            bid, ask = float(bid or 0), float(ask or 0)
        self._update_as_extremes_from_tob(bid, ask, ts)
        if self._bar_key is None:
            self._bar_key = key
        if key == self._bar_key:
            return
        self._ingest_book(book, ts)
        self._bar_key = key

    def _ingest_book(self, book, ts_ns: int) -> None:
        snap = snap25_from_book(
            book,
            out_levels=int(self.config.feature_levels),
            take_levels=int(self.config.book_depth),
        )
        if snap is None:
            return
        bid = snap["bid_p0"]
        ask = snap["ask_p0"]
        mid = 0.5 * (bid + ask)
        ts_us = ts_ns // 1_000 if ts_ns > 10**15 else (ts_ns if ts_ns > 10**12 else ts_ns * 1_000)
        sec = int(ts_us // 1_000_000)

        self._update_as_extremes_from_tob(bid, ask, ts_ns)

        row = {"timestamp": float(ts_us), "sec": float(sec), **snap}
        self._snap_hist.append(row)
        self._last_bid = bid
        self._last_ask = ask
        self._mid_hist.append(mid)

        self._flush_trades_into_history(sec)
        self._bars += 1

        if not self.config.use_fair_mid:
            return
        if self._bars < self.config.fair_min_bars:
            if not self._warmup_logged and self._bars % 30 == 0:
                self.log.info(
                    f"Snap25 warmup {self._bars}/{self.config.fair_min_bars}s",
                    color=LogColor.BLUE,
                )
            return
        if not self._warmup_logged:
            self._warmup_logged = True
            self.log.info("Snap25 warmup done — publishing fair mid", color=LogColor.GREEN)
        every = max(int(self.config.fair_predict_every_bars), 1)
        if self._bars % every == 0:
            self._publish_prediction(ts_ns, mid)

    def _flush_trades_into_history(self, sec: int) -> None:
        if not self._cur_trades:
            return
        raw = pd.DataFrame(self._cur_trades)
        self._cur_trades = []
        agg = aggregate_trades_1s(raw)
        if agg.empty:
            return
        # Keep only recent trade seconds overlapping snap history.
        keep_secs = {int(r["sec"]) for r in self._snap_hist}
        for _, tr in agg.iterrows():
            s = int(tr["sec"])
            if s not in keep_secs and abs(s - sec) > 2:
                continue
            self._trade_rows.append(tr.to_dict())
        # Cap trade history length
        max_n = int(self.config.history_bars) + 50
        if len(self._trade_rows) > max_n:
            self._trade_rows = self._trade_rows[-max_n:]

    def _fit_as(self, ts_init: int) -> None:
        n = len(self._as_last_bid)
        if n < self.config.min_bars:
            return
        bids = np.asarray(self._as_last_bid, dtype=float)
        asks = np.asarray(self._as_last_ask, dtype=float)
        min_bid = np.asarray(self._as_min_bid, dtype=float)
        max_ask = np.asarray(self._as_max_ask, dtype=float)
        mids = (bids + asks) / 2.0
        ave_time = float(self.config.bar_ms) * max(n - 1, 1) / n
        sigma_live = estimate_sigma(mids, ave_time_ms=ave_time)

        try:
            params = estimate_params(
                bids,
                asks,
                min_bid,
                max_ask,
                tick=self._tick,
                gamma=self.config.gamma,
                n_levels=self.config.n_levels_as,
                bar_ms=float(self.config.bar_ms),
            )
        except (ValueError, np.linalg.LinAlgError, RuntimeError) as exc:
            # Still refresh σ when intensity is sparse; keep last good A/k.
            if sigma_live > 0 and np.isfinite(sigma_live):
                params = ASParams(
                    sigma=sigma_live,
                    A=self._as_params.A,
                    k=self._as_params.k,
                    gamma=self.config.gamma,
                )
                self._as_params = params
                self.log.warning(
                    f"AS intensity skip ({exc}); sigma→{sigma_live:.6f} "
                    f"keep A={params.A:.4f} k={params.k:.4f} "
                    f"bid0={params.bid_spread(0):.6f}"
                )
                self.publish_data(
                    data_type=DataType(
                        ModelUpdate, metadata={"instrument_id": self.instrument_id.value}
                    ),
                    data=ModelUpdate(
                        sigma=params.sigma,
                        A=params.A,
                        k=params.k,
                        gamma=params.gamma,
                        ts_init=ts_init,
                    ),
                )
            else:
                self.log.warning(
                    f"Skip AS param fit ({exc}); keep A={self._as_params.A:.4f} "
                    f"k={self._as_params.k:.4f} sigma={self._as_params.sigma:.6f}"
                )
            return

        self._as_params = params
        self.log.info(
            f"AS params sigma={params.sigma:.6f} A={params.A:.4f} k={params.k:.4f} "
            f"bid0={params.bid_spread(0):.6f} ask0={params.ask_spread(0):.6f}",
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

    def _publish_prediction(self, ts_init: int, mid: float) -> None:
        if self._model is None or mid <= 0:
            return
        # bookTicker mid is authoritative; L2 can freeze after testnet TLS drops.
        bbo_mid = mid
        if self._cur_last_bid > 0 and self._cur_last_ask > self._cur_last_bid:
            bbo_mid = 0.5 * (self._cur_last_bid + self._cur_last_ask)
        if bbo_mid > 0 and mid > 0:
            drift_bp = abs(mid - bbo_mid) / bbo_mid * 1e4
            if drift_bp > self._stale_book_bp:
                if ts_init - self._stale_book_log_ns >= 10_000_000_000:
                    self._stale_book_log_ns = ts_init
                    self.log.warning(
                        f"Stale L2 mid={mid:.2f} vs BBO={bbo_mid:.2f} "
                        f"({drift_bp:.1f}bp) — publish neutral fair"
                    )
                # Neutral theo on live BBO so strategy does not quote off a frozen book.
                self.publish_data(
                    data_type=DataType(
                        Prediction, metadata={"instrument_id": self.instrument_id.value}
                    ),
                    data=Prediction(
                        prediction=bbo_mid, pred_ret=0.0, mid=bbo_mid, ts_init=ts_init
                    ),
                )
                return
        try:
            pred = self._predict_ret()
        except Exception as exc:
            # Avoid 1 Hz spam; one warn per 30s is enough for ops.
            if ts_init - self._predict_fail_logged_ns >= 30_000_000_000:
                self._predict_fail_logged_ns = ts_init
                self.log.warning(f"Skip snap25 predict: {exc}")
            return
        pred = float(np.clip(pred, -self._y_clip, self._y_clip))
        # aqsmodel.py: mid_pred = mid_price * (pred + 1) — always apply pred.
        # Optional soft gate only if meta.signal_threshold > 0 (research models).
        if self._signal_threshold > 0 and abs(pred) < self._signal_threshold:
            pred = 0.0
        # Apply pred on live BBO so theo tracks the market even if L2 lags a tick.
        theo_mid = bbo_mid if bbo_mid > 0 else mid
        theo = theo_mid * (1.0 + pred)
        if ts_init - self._pred_log_ns >= 10_000_000_000:
            self._pred_log_ns = ts_init
            self.log.info(
                f"fair mid={theo_mid:.2f} pred_ret={pred:+.6f} theo={theo:.2f} "
                f"delta={theo - theo_mid:+.2f}",
            )
        self.publish_data(
            data_type=DataType(Prediction, metadata={"instrument_id": self.instrument_id.value}),
            data=Prediction(prediction=theo, pred_ret=pred, mid=theo_mid, ts_init=ts_init),
        )

    def _predict_ret(self) -> float:
        """Mirror offline `feature_frame` (sans label): snap → trades → moment/gap."""
        snap = pd.DataFrame(list(self._snap_hist))
        if snap.empty:
            raise ValueError("empty snap history")
        need = ["timestamp", "sec", *SNAP_COLS]
        for c in need:
            if c not in snap.columns:
                raise ValueError(f"missing {c}")
        feat = calculate_features(snap[need])
        bars = aggregate_1s_features(feat)
        trades_1s = pd.DataFrame(self._trade_rows) if self._trade_rows else None
        if trades_1s is not None and not trades_1s.empty and "sec" in trades_1s.columns:
            # Already aggregated; pass through merge
            pass
        else:
            trades_1s = None
        bars = merge_trade_features(bars, trades_1s)
        # Same step as feature_frame(): VolumeStd/Skew/Kurt + VPIN_60 etc.
        bars = _add_moment_and_gap(bars)
        missing = [c for c in self._features if c not in bars.columns]
        if missing:
            raise ValueError(f"feature columns missing: {missing[:5]}")
        row = bars.iloc[[-1]][self._features].astype(float)
        if not np.isfinite(row.to_numpy()).all():
            row = row.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        # DataFrame keeps feature names → no sklearn UserWarning spam.
        return float(self._model.predict(row)[0])
