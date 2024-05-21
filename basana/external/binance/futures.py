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
from typing import Any, Dict, List, Optional

from . import common, helpers, futures_requests
from .client import futures as futures_client
from basana.core.enums import OrderOperation
from basana.core.pair import FuturesPair


Balance = common.Balance
CanceledOCOOrder = common.CanceledOCOOrder
CanceledOrder = common.CanceledOrder
CreatedOCOOrder = common.CreatedOCOOrder
OCOOrderInfo = common.OCOOrderInfo
OCOOrderWrapper = common.OCOOrderWrapper
OrderInfo = common.OrderInfo

FuturesBalance = common.FuturesBalance


class Trade(common.Trade):
    @property
    def order_list_id(self) -> Optional[str]:
        """The order list id."""
        ret = self.json.get("orderListId")
        ret = None if ret in [None, -1] else str(ret)
        return ret


class Fill(common.Fill):
    @property
    def trade_id(self) -> str:
        """The trade id."""
        return str(self.json["tradeId"])


class CreatedOrder(common.CreatedOrder):
    @property
    def order_list_id(self) -> Optional[str]:
        """The order list id."""
        ret = self.json["orderListId"]
        ret = None if ret == -1 else str(ret)
        return ret

    @property
    def fills(self) -> List[Fill]:
        # Only available for FULL responses.
        return [Fill(fill) for fill in self.json.get("fills", [])]


class OpenOrder(common.OpenOrder):
    @property
    def order_list_id(self) -> Optional[str]:
        """The order list id."""
        ret = self.json.get("orderListId")
        ret = None if ret in [None, -1] else str(ret)
        return ret

    @property
    def quote_amount(self) -> Optional[Decimal]:
        """The order amount in quote units."""
        return helpers.get_optional_decimal(self.json, "origQuoteOrderQty", True)


class Account:
    """Futures account."""

    def __init__(self, cli: futures_client.FuturesAccount):
        self._cli = cli

    async def get_balances(self) -> FuturesBalance:
        """Returns all balances."""
        account_info = await self._cli.get_account_information()
        return FuturesBalance(account_info)

    async def create_order(self, order_request: futures_requests.ExchangeOrder) -> CreatedOrder:
        created_order = await order_request.create_order(self._cli)
        return CreatedOrder(created_order)

    async def create_market_order(
        self,
        operation: OrderOperation,
        pair: FuturesPair,
        amount: Decimal,
        client_order_id: Optional[str] = None,
        **kwargs: Dict[str, Any]
    ) -> CreatedOrder:
        """Creates a market order.

        Check https://binance-docs.github.io/apidocs/futures/cn/#trade-3 for more information.
        If the order can't be created a :class:`basana.external.binance.exchange.Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The amount to buy/sell in base units.
        :param client_order_id: A client order id.
        :param kwargs: Additional keyword arguments that will be forwarded.

        .. note::

          * Either amount or quote_amount should be set, but not both.
        """

        return await self.create_order(
            futures_requests.MarketOrder(
                operation, pair, amount=amount, client_order_id=client_order_id, **kwargs
            )
        )

    async def create_limit_order(
        self,
        operation: OrderOperation,
        pair: FuturesPair,
        amount: Decimal,
        limit_price: Decimal,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None,
        **kwargs: Dict[str, Any]
    ) -> CreatedOrder:
        """Creates a limit order.

        Check https://binance-docs.github.io/apidocs/futures/cn/#trade-3 for more information.
        If the order can't be created a :class:`basana.external.binance.exchange.Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The amount to buy/sell in base units.
        :param limit_price: The limit price.
        :param time_in_force: The time in force.
        :param client_order_id: A client order id.
        :param kwargs: Additional keyword arguments that will be forwarded.
        """

        return await self.create_order(
            futures_requests.LimitOrder(
                operation,
                pair,
                amount,
                limit_price,
                time_in_force=time_in_force,
                client_order_id=client_order_id,
                **kwargs
            )
        )

    async def create_stop_limit_order(
        self,
        operation: OrderOperation,
        pair: FuturesPair,
        amount: Decimal,
        stop_price: Decimal,
        limit_price: Decimal,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None,
        **kwargs: Dict[str, Any]
    ) -> CreatedOrder:
        """Creates a stop limit order.

        Check https://binance-docs.github.io/apidocs/futures/cn/#trade-3 for more information.
        If the order can't be created a :class:`basana.external.binance.exchange.Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The amount to buy/sell in base units.
        :param stop_price: The stop price.
        :param limit_price: The limit price.
        :param time_in_force: The time in force.
        :param client_order_id: A client order id.
        :param kwargs: Additional keyword arguments that will be forwarded.
        """

        return await self.create_order(
            futures_requests.StopLimitOrder(
                operation,
                pair,
                amount,
                stop_price,
                limit_price,
                time_in_force=time_in_force,
                client_order_id=client_order_id,
                **kwargs
            )
        )

    async def get_order_info(
        self,
        pair: FuturesPair,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
        include_trades: bool = True,
    ) -> OrderInfo:
        """Returns information about an order.

        :param pair: The trading pair.
        :param order_id: The order id.
        :param client_order_id: The client order id.
        :param include_trades: True to include trades in the order info, False otherwise.

        .. note::

          * Either order_id or client_order_id should be set, but not both.
          * Including trades requires making an extra request to Binance.
        """
        order_book_symbol = helpers.pair_to_order_book_symbol(pair)
        order_info = await self._cli.query_order(
            order_book_symbol,
            order_id=None if order_id is None else int(order_id),
            orig_client_order_id=client_order_id,
        )
        trades = []
        if include_trades:
            trades = [
                Trade(trade) for trade in await self._cli.get_trades(order_book_symbol, order_id=order_info["orderId"])
            ]
        return OrderInfo(order_info, trades)

    async def get_open_orders(self, pair: Optional[FuturesPair] = None) -> List[OpenOrder]:
        """Returns open orders.

        :param pair: If set, only open orders matching this pair will be returned, otherwise all open orders will be
            returned.
        """

        order_book_symbol = None
        if pair:
            order_book_symbol = helpers.pair_to_order_book_symbol(pair)
        return [OpenOrder(open_order) for open_order in await self._cli.get_open_orders(order_book_symbol)]

    async def cancel_order(
        self,
        pair: FuturesPair,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> CanceledOrder:
        """Cancels an order.

        If the order can't be canceled a :class:`basana.external.binance.exchange.Error` will be raised.

        :param pair: The trading pair.
        :param order_id: The order id.
        :param client_order_id: The client order id.

        .. note::

          * Either order_id or client_order_id should be set, but not both.
        """
        canceled_order = await self._cli.cancel_order(
            helpers.pair_to_order_book_symbol(pair),
            order_id=None if order_id is None else int(order_id),
            orig_client_order_id=client_order_id,
        )
        return CanceledOrder(canceled_order)
