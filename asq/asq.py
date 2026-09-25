#-------------------------------------------------------------------------------------------------
# Copyright 2023 Jerry Li @ Positive Venture Group
#
# This file is a template for Q-quant market making strategies as Avelleneda-Stoikov (AS) market maker.
# This strategy is based on tick level data and is designed for HFT market making.
#-------------------------------------------------------------------------------------------------

from decimal import Decimal
from typing import Optional
import numpy as np
import datetime

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.enums import book_type_from_str
from nautilus_trader.model.identifiers import InstrumentId, PositionId
from nautilus_trader.model.position import Position
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.book import OrderBook
from nautilus_trader.model.data import BookOrder
from nautilus_trader.model.data import OrderBookDelta
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.events import (
    PositionClosed,
    PositionEvent,
    PositionOpened,
)


# *** Avelleneda-Stoikov (AS) Market making model. ***
# *** In the initial model, it loses from trades themselves and profits from the maker transaction fee rebate. ***


class ASQConfig(StrategyConfig):
    """
    Configuration for ASQMarketMaking instances.

    Parameters
    ---
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    max_trade_size : str
        The max position size per trade (volume on the level can be less).
    trigger_min_size : float
        The minimum size on the larger side to trigger an order.
    order_id_tag : str
        The unique order ID tag for the strategy. Must be unique
        amongst all running strategies for a particular trader ID.
    oms_type : OmsType
        The order management system type for the strategy. This will determine how the 'ExecutionEngine' handles position IDs (see docs).
    book_type : BookType {'L1_TBBO', 'L2_MBP', 'L3_MBO'}
        The order book type to use for the strategy.
    use_quote_ticks : bool
        Whether to use quote ticks instead of order book data. When set to True, the strategy will use the 'L1_TBBO' orderbook and subscribe quote tick data no matter what the book_type is; When set to False, the strategy will use the book_type orderbook and subscribe to orderbook delta data
    subscribe_ticker : bool
        Whether to subscribe to ticker data. When set to True, the strategy will subscribe to ticker data in addition to the data source specified by book_type and use_quote_ticks.
    max_quantity: int
        The maximum position quantity (constraint).
    current_quantity: int
        The current notional position quantity.
    order_quantity: int
        The order quantity per trade.
    expire_time_s:
        The duration of expiration after a new order is sent
    A: float
        The parameter of the exponential market speed function (\(y = A * \exp(-k * x)\)).
    k: float
        The parameter of the number of times of the exponential market speed function.
    sigma: float
        The volatility (std) of the target price model, e.g. the mid price, the micro price, DMP, JMP, etc.
    gamma: float
        The risk aversion parameter, usually and by default 0.01.
    """

    instrument_id: str
    max_trade_size: Decimal
    trigger_min_size: float = 0.5
    book_type: str = "L2_MBP"
    use_quote_ticks: bool = False
    subscribe_ticker: bool = False
    max_quantity: int = 0
    current_quantity: int = 0
    order_quantity: int = 0
    expire_time_s: int = 1
    A: float = 0.1
    k: float = 0.1
    sigma: float = 0.01
    gamma: float = 0.01
    _position_id: int = 0


class ASQMarketMaking(Strategy):
    """
    A simple strategy that sends FOK limit orders on every tick with the calculated optimal bid and ask price.
    The strategy sends limit orders on both sides every tick until the quantity of the position reaches the quantity limit Q.
    When the position quantity reaches the quantity limit Q, the strategy will stop sending order on both sides and just send
    to the opposite side of direction of the current position.
    Cancels all orders and closes all positions on stop.

    Parameters
    ---
    config : OrderbookImbalanceConfig
        The configuration for the instance.
    """

    def __init__(self, config: ASQConfig):
        assert config.max_quantity > 0
        super().__init__(config)

        # Configuration
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.max_trade_size = Decimal(config.max_trade_size)
        self.trigger_min_size = config.trigger_min_size
        self.instrument: Optional[Instrument] = None
        self.max_quantity = config.max_quantity
        self.current_quantity = config.current_quantity
        self.order_quantity = config.order_quantity
        self.A = config.A
        self.k = config.k
        self.sigma = config.sigma
        self.gamma = config.gamma
        self.expire_time_s = config.expire_time_s
        
        if self.config.use_quote_ticks:
            assert self.config.book_type == "L1_TBBO"
            
        self.book_type: BookType = book_type_from_str(self.config.book_type)
        self._book = None  # type: Optional[OrderBook]
        self._position_id = config._position_id
        self.event_time = 0

    def on_start(self):
        """Actions to be performed on strategy start."""
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return

        if self.config.use_quote_ticks:
            book_type = BookType.L1_TBBO
            self.subscribe_quote_ticks(self.instrument.id)
        else:
            book_type = book_type_from_str(self.config.book_type)
            self.subscribe_order_book_deltas(self.instrument.id, book_type)
        
        if self.config.subscribe_ticker:
            self.subscribe_ticker(self.instrument.id)
        
        self._book = OrderBook(instrument_id=self.instrument.id, book_type=book_type)

    def on_event(self, event: PositionEvent):
        """Calculate the notional quantities."""
        if isinstance(event, (PositionOpened, PositionClosed)):
            position = self.cache.position(event.position_id)
            side_num = 1
            if position.is_short:  # Short position
                side_num = -1
            if isinstance(event, PositionClosed):
                side_num = -side_num
            self.current_quantity = self.current_quantity + side_num * position.quantity

    def on_order_book_delta(self, data: OrderBookDelta):
        """Actions to be performed when a delta is received."""
        if not self._book:
            self.log.error("No book being maintained.")
            return

        self.event_time = data.ts_event
        self._book.apply(data)
        if self._book.spread():
            self.check_trigger()

    def on_quote_tick(self, tick: QuoteTick):
        """Actions to be performed when a quote_tick (level 1 best bid & ask px & qty) is received."""
        bid = BookOrder(
            price=tick.bid.as_double(),
            size=tick.bid_size.as_double(),
            side=OrderSide.BUY,
        )
        ask = BookOrder(
            price=tick.ask.as_double(),
            size=tick.ask_size.as_double(),
            side=OrderSide.SELL,
        )
        self.event_time = tick.ts_event
        self._book.clear()
        self._book.update(bid)
        self._book.update(ask)
        if self._book.spread():
            self.check_trigger()

    def on_order_book(self, order_book: OrderBook):
        """Actions to be performed when an order book update is received."""
        self._book = order_book
        if self._book.spread():
            self.check_trigger()

    def check_trigger(self):
        """Check for trigger conditions."""
        if not self._book:
            self.log.error("No book being maintained.")
            return

        if not self.instrument:
            self.log.error("No instrument loaded.")
            return

        bid_size = self._book.best_bid_qty()
        ask_size = self._book.best_ask_qty()
        if not (bid_size and ask_size):
            return

        # Calculate spreads and submit orders
        mid_price = self.get_mid_price()
        
        bid_price = mid_price - self.get_bid_spread(
            self.sigma, self.A, self.k, self.gamma, self.current_quantity
        )
        ask_price = mid_price + self.get_ask_spread(
            self.sigma, self.A, self.k, self.gamma, self.current_quantity
        )

        total_expire_time_s = self.expire_time_s + self.event_time / 1e9
        expire_time_datetime = datetime.datetime.fromtimestamp(
            total_expire_time_s, tz=datetime.timezone.utc
        )

        bid_order = self.order_factory.limit(
            instrument_id=self.instrument.id,
            price=self.instrument.make_price(bid_price),
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.order_quantity),
            post_only=False,
            time_in_force=TimeInForce.GTD,
            expire_time=expire_time_datetime
        )
        
        ask_order = self.order_factory.limit(
            instrument_id=self.instrument.id,
            price=self.instrument.make_price(ask_price),
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(self.order_quantity),
            post_only=False,
            time_in_force=TimeInForce.GTD,
            expire_time=expire_time_datetime
        )

        if self._position_id >= 50:
            self._position_id = 0
            
        if self.current_quantity >= self.max_quantity:
            self.submit_order(ask_order, PositionId(f"short-{self._position_id}"))
            self.log.info(f"only short-{self._position_id}")
            self._position_id = self._position_id + 1
        elif self.current_quantity <= -self.max_quantity:
            self.submit_order(bid_order, PositionId(f"long-{self._position_id}"))
            self.log.info(f"only long-{self._position_id}")
            self._position_id = self._position_id + 1
        else:
            self.submit_order(bid_order, PositionId(f"long-{self._position_id}"))
            self.submit_order(ask_order, PositionId(f"short-{self._position_id}"))
            self.log.info(f"long and short-{self._position_id}")
            self._position_id = self._position_id + 1

    def get_bid_spread(self, sigma, A, k, gamma, q):
        """Calculate bid spread based on Avelleneda-Stoikov model."""
        var1 = (1 / gamma) * np.log(1 + gamma / k)
        var2 = (2 * float(q) + 1) / 2 * np.sqrt(
            sigma ** 2 * gamma / (2 * k * A) * (1 + gamma / k) ** (1 + k / gamma)
        )
        return var1 + var2

    def get_ask_spread(self, sigma, A, k, gamma, q):
        """Calculate ask spread based on Avelleneda-Stoikov model."""
        var1 = (1 / gamma) * np.log(1 + gamma / k)
        var2 = (2 * float(q) - 1) / 2 * np.sqrt(
            sigma ** 2 * gamma / (2 * k * A) * (1 + gamma / k) ** (1 + k / gamma)
        )
        return var1 - var2

    def get_mid_price(self):
        """Calculate mid price from order book."""
        return (self._book.best_ask_price() + self._book.best_bid_price()) / 2

    def on_stop(self):
        """Actions to be performed when the strategy is stopped."""
        if self.instrument is None:
            return
        self.cancel_all_orders(self.instrument.id)
        self.close_all_positions(self.instrument.id)