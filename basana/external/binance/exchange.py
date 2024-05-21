# Basana
#
# Copyright 2022-2023 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from decimal import Decimal
from typing import cast, Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union
import dataclasses

import aiohttp

from . import (
    client,
    helpers,
    order_book,
    trades,
    websockets as binance_ws,
    spot,
    cross_margin,
    isolated_margin,
    futures,
    klines,
    common,
    contract,
)
from basana.core import bar, dispatcher, enums, event, token_bucket, websockets as core_ws
from basana.core.pair import Pair, PairInfo, FuturesPair, FuturesPairInfo


@dataclasses.dataclass(frozen=True)
class PairInfoEx(PairInfo):
    """Information about a trading pair.

    :param base_precision: The precision for the base symbol.
    :param quote_precision: The precision for the quote symbol.
    :param permissions: The account and pair permissions.

    Check **Account and Symbol Permissions** in https://binance-docs.github.io/apidocs/spot/en/#public-api-definitions.
    """

    #: The account and pair permissions.
    permissions: List[str]


@dataclasses.dataclass(frozen=True)
class FuturesPairInfoEx(FuturesPairInfo):
    """Information about a trading pair.

    :param base_precision: The precision for the base symbol.
    :param quote_precision: The precision for the quote symbol.
    :param permissions: The account and pair permissions.

    Check **Account and Symbol Permissions** in https://binance-docs.github.io/apidocs/spot/en/#public-api-definitions.
    """

    #: The account and pair permissions.
    permissions: List[str]


BarEventHandler = Callable[[bar.BarEvent], Awaitable[Any]]
Error = client.Error
OrderBookEvent = order_book.OrderBookEvent
OrderBookEventHandler = Callable[[order_book.OrderBookEvent], Awaitable[Any]]
OrderOperation = enums.OrderOperation
TradeEvent = trades.TradeEvent
TradeEventHandler = Callable[[trades.TradeEvent], Awaitable[Any]]
BinanceAccountType = common.BinanceAccountType
BinanceContractType = contract.BinanceContractType


class SpotExchange:
    """A client for `Binance <https://www.binance.com/>`_ crypto currency exchange.

    :param dispatcher: The event dispatcher.
    :param api_key: An optional api key. If not set only public endpoints can be used.
    :param api_secret: An optional api secret. If not set only public endpoints can be used.
    :param session: An optional client session, in case you want to reuse connections.
    :type session: aiohttp.ClientSession
    :param tb: An optional token bucket limiter, in case you want to throttle requests.
    :param config_overrides: An optional dictionary for overriding config settings.
    """

    def __init__(
        self,
        dispatcher: dispatcher.EventDispatcher,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        tb: Optional[token_bucket.TokenBucketLimiter] = None,
        config_overrides: dict = {},
        account_type: BinanceAccountType = BinanceAccountType.SPOT,
        testnet: bool = False,
    ):
        self._dispatcher = dispatcher
        self._account_type = account_type
        if self._account_type.is_spot_or_margin:
            self._cli: client.RestClient = client.APIClient(
                api_key=api_key,
                api_secret=api_secret,
                session=session,
                tb=tb,
                config_overrides=config_overrides,
                api_type="api_testnet" if testnet else "api",
            )
        else:
            raise ValueError("Invalid account_type")
        self._session = session
        self._tb = tb
        self._config_overrides = config_overrides
        self._websocket: Optional[binance_ws.WebSocketClient] = None
        self._channel_to_event_source: Dict[str, event.EventSource] = {}
        self._pair_info_cache: Dict[Pair, PairInfoEx] = {}

    def subscribe_to_bar_events(
        self,
        pair: Pair,
        bar_duration: Union[int, str],
        event_handler: BarEventHandler,
        skip_first_bar: bool = True,
        flush_delay: float = 1,
    ):
        """Registers an async callable that will be called when a new bar is available.

        Works as defined in https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-streams but only closed
        klines are reported.

        :param pair: The trading pair.
        :param bar_duration: The bar duration. One of 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M.
        :type bar_duration: str
        :param event_handler: An async callable that receives a BarEvent.
        :param skip_first_bar: Ignored. It will be removed in a future version.
        :param flush_delay: Ignored. It will be removed in a future version.
        """
        # TODO: Deprecate support for bar_duration as int.
        # TODO: Remove skip_first_bar and flush_delay.
        interval = {
            # Supporting interval as int for backwards compatibility reasons.
            1: "1s",
            60: "1m",
            3 * 60: "3m",
            5 * 60: "5m",
            15 * 60: "15m",
            30 * 60: "30m",
            3600: "1h",
            2 * 3600: "2h",
            4 * 3600: "4h",
            6 * 3600: "6h",
            8 * 3600: "8h",
            12 * 3600: "12h",
            86400: "1d",
            3 * 86400: "3d",
            7 * 86400: "1w",
            31 * 86400: "1M",
            # Once support for interval as int is removed, this should be simplified.
            "1s": "1s",
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "2h": "2h",
            "4h": "4h",
            "6h": "6h",
            "8h": "8h",
            "12h": "12h",
            "1d": "1d",
            "3d": "3d",
            "1w": "1w",
            "1M": "1M",
        }.get(bar_duration)
        assert interval, "Invalid bar_duration"

        channel = klines.get_channel(pair, interval)
        self._subscribe_to_ws_channel_events(
            channel,
            lambda ws_cli: klines.WebSocketEventSource(pair, ws_cli),
            cast(dispatcher.EventHandler, event_handler),
        )

    def subscribe_to_order_book_events(self, pair: Pair, event_handler: OrderBookEventHandler, depth: int = 10):
        """Registers an async callable that will be called every 1 second with the top bids/asks of the order book.

        Works as defined in https://binance-docs.github.io/apidocs/spot/en/#partial-book-depth-streams.

        :param pair: The trading pair.
        :param event_handler: An async callable that receives an OrderBookEvent.
        :param depth: The order book depth. Valid values are: 5, 10, 20.
        """
        channel = order_book.get_channel(pair, depth)
        self._subscribe_to_ws_channel_events(
            channel,
            lambda ws_cli: order_book.WebSocketEventSource(pair, ws_cli),
            cast(dispatcher.EventHandler, event_handler),
        )

    def subscribe_to_trade_events(self, pair: Pair, event_handler: TradeEventHandler):
        """Registers an async callable that will be called for every new trade.

        Works as defined in https://binance-docs.github.io/apidocs/spot/en/#trade-streams.

        :param pair: The trading pair.
        :param event_handler: An async callable that receives a TradeEvent.
        """
        channel = trades.get_channel(pair)
        self._subscribe_to_ws_channel_events(
            channel,
            lambda ws_cli: trades.WebSocketEventSource(pair, ws_cli),
            cast(dispatcher.EventHandler, event_handler),
        )

    async def get_pair_info(self, pair: Pair) -> PairInfoEx:
        """Returns information about a trading pair.

        :param pair: The trading pair.
        """
        ret = self._pair_info_cache.get(pair)
        if not ret:
            exchange_info = await self._cli.get_exchange_info(helpers.pair_to_order_book_symbol(pair))
            symbols = exchange_info["symbols"]
            assert len(symbols) == 1, "More than 1 symbol found"
            symbol_info = symbols[0]
            price_filter = get_filter_from_symbol_info(symbol_info, "PRICE_FILTER")
            assert price_filter, f"PRICE_FILTER not found for {pair}"
            lot_size = get_filter_from_symbol_info(symbol_info, "LOT_SIZE")
            assert lot_size, f"LOT_SIZE not found for {pair}"
            ret = PairInfoEx(
                base_precision=get_precision_from_step_size(lot_size["stepSize"]),
                quote_precision=get_precision_from_step_size(price_filter["tickSize"]),
                permissions=symbol_info.get("permissions"),
            )
            self._pair_info_cache[pair] = ret
        return ret

    async def get_bid_ask(self, pair: Pair) -> Tuple[Decimal, Decimal]:
        """Returns the current bid and ask price.

        :param pair: The trading pair.
        """
        order_book = await self._cli.get_order_book(helpers.pair_to_order_book_symbol(pair), limit=1)
        return Decimal(order_book["bids"][0][0]), Decimal(order_book["asks"][0][0])

    @property
    def spot_account(self) -> spot.Account:
        """Returns the spot account."""
        return spot.Account(self._cli.spot_account)

    @property
    def cross_margin_account(self) -> cross_margin.Account:
        """Returns the cross margin account."""
        return cross_margin.Account(self._cli.cross_margin_account)

    @property
    def isolated_margin_account(self) -> isolated_margin.Account:
        """Returns the isolated margin account."""
        return isolated_margin.Account(self._cli.isolated_margin_account)

    def _subscribe_to_ws_channel_events(
        self,
        channel: str,
        event_src_factory: Callable[[core_ws.WebSocketClient], core_ws.ChannelEventSource],
        event_handler: dispatcher.EventHandler,
    ):
        # Get/create the event source for the channel.
        ws_cli = self._get_ws_client()
        event_source = ws_cli.get_channel_event_source(channel)
        if not event_source:
            event_source = event_src_factory(ws_cli)
            ws_cli.set_channel_event_source(channel, event_source)

        # Subscribe the event handler to the event source.
        self._dispatcher.subscribe(event_source, event_handler)

    def _get_ws_client(self) -> binance_ws.WebSocketClient:
        if self._websocket is None:
            self._websocket = binance_ws.WebSocketClient(session=self._session, config_overrides=self._config_overrides)
        return self._websocket


class FuturesExchange:
    """A client for `Binance <https://www.binance.com/>`_ crypto currency exchange.

    :param dispatcher: The event dispatcher.
    :param api_key: An optional api key. If not set only public endpoints can be used.
    :param api_secret: An optional api secret. If not set only public endpoints can be used.
    :param session: An optional client session, in case you want to reuse connections.
    :type session: aiohttp.ClientSession
    :param tb: An optional token bucket limiter, in case you want to throttle requests.
    :param config_overrides: An optional dictionary for overriding config settings.
    """

    def __init__(
        self,
        dispatcher: dispatcher.EventDispatcher,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        tb: Optional[token_bucket.TokenBucketLimiter] = None,
        config_overrides: dict = {},
        account_type: BinanceAccountType = BinanceAccountType.USDT_FUTURE,
        testnet: bool = False,
    ):
        self._dispatcher = dispatcher
        self._account_type = account_type
        if self._account_type == BinanceAccountType.USDT_FUTURE:
            self._cli: client.RestClient = client.FAPIClient(
                api_key=api_key,
                api_secret=api_secret,
                session=session,
                tb=tb,
                config_overrides=config_overrides,
                api_type="fapi_testnet" if testnet else "fapi",
            )
        else:
            raise ValueError("Invalid account_type")
        self._session = session
        self._tb = tb
        self._config_overrides = config_overrides
        self._websocket: Optional[binance_ws.WebSocketClient] = None
        self._channel_to_event_source: Dict[str, event.EventSource] = {}
        self._pair_info_cache: Dict[FuturesPair, FuturesPairInfoEx] = {}

    def subscribe_to_bar_events(
        self,
        pair: Pair,
        bar_duration: Union[int, str],
        event_handler: BarEventHandler,
        skip_first_bar: bool = True,
        flush_delay: float = 1,
    ):
        """Registers an async callable that will be called when a new bar is available.

        Works as defined in https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-streams but only closed
        klines are reported.

        :param pair: The trading pair.
        :param bar_duration: The bar duration. One of 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M.
        :type bar_duration: str
        :param event_handler: An async callable that receives a BarEvent.
        :param skip_first_bar: Ignored. It will be removed in a future version.
        :param flush_delay: Ignored. It will be removed in a future version.
        """
        # TODO: Deprecate support for bar_duration as int.
        # TODO: Remove skip_first_bar and flush_delay.
        interval = {
            # Supporting interval as int for backwards compatibility reasons.
            1: "1s",
            60: "1m",
            3 * 60: "3m",
            5 * 60: "5m",
            15 * 60: "15m",
            30 * 60: "30m",
            3600: "1h",
            2 * 3600: "2h",
            4 * 3600: "4h",
            6 * 3600: "6h",
            8 * 3600: "8h",
            12 * 3600: "12h",
            86400: "1d",
            3 * 86400: "3d",
            7 * 86400: "1w",
            31 * 86400: "1M",
            # Once support for interval as int is removed, this should be simplified.
            "1s": "1s",
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "2h": "2h",
            "4h": "4h",
            "6h": "6h",
            "8h": "8h",
            "12h": "12h",
            "1d": "1d",
            "3d": "3d",
            "1w": "1w",
            "1M": "1M",
        }.get(bar_duration)
        assert interval, "Invalid bar_duration"

        channel = klines.get_channel(pair, interval)
        self._subscribe_to_ws_channel_events(
            channel,
            lambda ws_cli: klines.WebSocketEventSource(pair, ws_cli),
            cast(dispatcher.EventHandler, event_handler),
        )

    def subscribe_to_order_book_events(self, pair: Pair, event_handler: OrderBookEventHandler, depth: int = 10):
        """Registers an async callable that will be called every 1 second with the top bids/asks of the order book.

        Works as defined in https://binance-docs.github.io/apidocs/spot/en/#partial-book-depth-streams.

        :param pair: The trading pair.
        :param event_handler: An async callable that receives an OrderBookEvent.
        :param depth: The order book depth. Valid values are: 5, 10, 20.
        """
        channel = order_book.get_channel(pair, depth)
        self._subscribe_to_ws_channel_events(
            channel,
            lambda ws_cli: order_book.WebSocketEventSource(pair, ws_cli),
            cast(dispatcher.EventHandler, event_handler),
        )

    def subscribe_to_trade_events(self, pair: Pair, event_handler: TradeEventHandler):
        """Registers an async callable that will be called for every new trade.

        Works as defined in https://binance-docs.github.io/apidocs/spot/en/#trade-streams.

        :param pair: The trading pair.
        :param event_handler: An async callable that receives a TradeEvent.
        """
        channel = trades.get_channel(pair)
        self._subscribe_to_ws_channel_events(
            channel,
            lambda ws_cli: trades.WebSocketEventSource(pair, ws_cli),
            cast(dispatcher.EventHandler, event_handler),
        )

    async def get_pair(
        self,
        symbol: Optional[str] = None,
        pair: Optional[str] = None,
        contract_type: Optional[BinanceContractType] = None,
    ) -> FuturesPair:
        """Returns a FuturesPair object.

        :param pair: The trading pair.
        :param contract_type: The contract type.
        """
        exchange_info = await self._cli.get_exchange_info()
        symbols = exchange_info["symbols"]
        symbols = filter(lambda x: x["pair"] == pair, symbols) if pair is not None else symbols
        symbols = (
            symbols if contract_type is None else filter(lambda x: x["contractType"] == contract_type.value, symbols)
        )
        symbols = symbols if symbol is None else filter(lambda x: x["symbol"] == symbol, symbols)
        symbols = list(symbols)
        assert len(symbols) > 0, "Symbol not found"
        assert len(symbols) == 1, "More than 1 symbol found"
        symbol_info = symbols[0]
        return FuturesPair(
            symbol=symbol_info["symbol"],
            base_symbol=symbol_info["baseAsset"],
            quote_symbol=symbol_info["quoteAsset"],
            contract_type=BinanceContractType(symbol_info["contractType"]),
            delivery_date=symbol_info.get("deliveryDate"),
        )

    async def get_pair_info(self, futures_pair: FuturesPair) -> FuturesPairInfoEx:
        """Returns information about a trading pair.

        :param pair: The trading pair.
        """
        ret = self._pair_info_cache.get(futures_pair)
        if not ret:
            exchange_info = await self._cli.get_exchange_info()

            symbols = exchange_info["symbols"]
            symbols = filter(lambda x: x["symbol"] == helpers.pair_to_order_book_symbol(futures_pair), symbols)
            symbols = filter(lambda x: x["contractType"] == futures_pair.contract_type.value, symbols)
            symbols = list(symbols)
            assert len(symbols) > 0, "Symbol not found"
            assert len(symbols) == 1, "More than 1 symbol found"
            symbol_info = symbols[0]
            price_filter = get_filter_from_symbol_info(symbol_info, "PRICE_FILTER")
            assert price_filter, f"PRICE_FILTER not found for {futures_pair}"
            lot_size = get_filter_from_symbol_info(symbol_info, "LOT_SIZE")
            assert lot_size, f"LOT_SIZE not found for {futures_pair}"
            ret = FuturesPairInfoEx(
                base_precision=get_precision_from_step_size(lot_size["stepSize"]),
                quote_precision=get_precision_from_step_size(price_filter["tickSize"]),
                contract_type=BinanceContractType(symbol_info["contractType"]),
                delivery_date=symbol_info.get("deliveryDate"),
                permissions=symbol_info.get("permissions"),
            )
            self._pair_info_cache[futures_pair] = ret
        return ret

    async def get_bid_ask(self, pair: Pair) -> Tuple[Decimal, Decimal]:
        """Returns the current bid and ask price.

        :param pair: The trading pair.
        """
        order_book = await self._cli.get_order_book(helpers.pair_to_order_book_symbol(pair), limit=1)
        return Decimal(order_book["bids"][0][0]), Decimal(order_book["asks"][0][0])

    @property
    def futures_account(self) -> futures.Account:
        """Returns the futures account."""
        return futures.Account(self._cli.futures_account)

    def _subscribe_to_ws_channel_events(
        self,
        channel: str,
        event_src_factory: Callable[[core_ws.WebSocketClient], core_ws.ChannelEventSource],
        event_handler: dispatcher.EventHandler,
    ):
        # Get/create the event source for the channel.
        ws_cli = self._get_ws_client()
        event_source = ws_cli.get_channel_event_source(channel)
        if not event_source:
            event_source = event_src_factory(ws_cli)
            ws_cli.set_channel_event_source(channel, event_source)

        # Subscribe the event handler to the event source.
        self._dispatcher.subscribe(event_source, event_handler)

    def _get_ws_client(self) -> binance_ws.WebSocketClient:
        if self._websocket is None:
            self._websocket = binance_ws.WebSocketClient(session=self._session, config_overrides=self._config_overrides)
        return self._websocket


# Factory method for creating an Exchange instance.
class Exchange:

    @classmethod
    def create(
        cls,
        dispatcher: dispatcher.EventDispatcher,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        tb: Optional[token_bucket.TokenBucketLimiter] = None,
        config_overrides: dict = {},
        account_type: BinanceAccountType = BinanceAccountType.SPOT,
        testnet: bool = False,
    ) -> Union[SpotExchange, FuturesExchange]:
        if account_type.is_spot_or_margin:
            return SpotExchange(dispatcher, api_key, api_secret, session, tb, config_overrides, account_type, testnet)
        elif account_type.is_futures:
            return FuturesExchange(
                dispatcher, api_key, api_secret, session, tb, config_overrides, account_type, testnet
            )
        else:
            raise ValueError("Invalid account_type")


def get_filter_from_symbol_info(symbol_info: dict, filter_type: str) -> Optional[dict]:
    filters = symbol_info["filters"]
    price_filters = [filter for filter in filters if filter["filterType"] == filter_type]
    return None if not price_filters else price_filters[0]


def get_precision_from_step_size(step_size: str) -> int:
    return int(-Decimal(step_size).log10() / Decimal(10).log10())
