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
from enum import Enum, unique
from decimal import Decimal
from typing import Dict, Optional, Sequence
import collections
import datetime

# from . import helpers
from . import helpers
from basana.core.enums import OrderOperation


@unique
class BinanceAccountType(Enum):
    """
    Represents a `Binance` account type.
    """

    SPOT = "SPOT"
    MARGIN = "MARGIN"
    ISOLATED_MARGIN = "ISOLATED_MARGIN"
    USDT_FUTURE = "USDT_FUTURE"
    COIN_FUTURE = "COIN_FUTURE"

    @property
    def is_spot(self):
        return self == BinanceAccountType.SPOT

    @property
    def is_margin(self):
        return self in (
            BinanceAccountType.MARGIN,
            BinanceAccountType.ISOLATED_MARGIN,
        )

    @property
    def is_spot_or_margin(self):
        return self in (
            BinanceAccountType.SPOT,
            BinanceAccountType.MARGIN,
            BinanceAccountType.ISOLATED_MARGIN,
        )

    @property
    def is_futures(self) -> bool:
        return self in (
            BinanceAccountType.USDT_FUTURE,
            BinanceAccountType.COIN_FUTURE,
        )




class Balance:
    def __init__(self, json: dict):
        self.json = json

    @property
    def available(self) -> Decimal:
        """The available balance."""
        return Decimal(self.json["free"])

    @property
    def total(self) -> Decimal:
        """The total balance (available + locked)."""
        return self.available + self.locked

    @property
    def locked(self) -> Decimal:
        """The locked balance."""
        return Decimal(self.json["locked"])


class Position:
    """
    {'symbol': 'SNTUSDT', 'initialMargin': '0', 'maintMargin': '0', 'unrealizedProfit': '0.00000000',
      'positionInitialMargin': '0', 'openOrderInitialMargin': '0', 'leverage': '20', 'isolated': False,
        'entryPrice': '0.0', 'breakEvenPrice': '0.0', 'maxNotional': '25000', 'positionSide': 'LONG',
          'positionAmt': '0', 'notional': '0', 'isolatedWallet': '0', 'updateTime': 0, 'bidNotional': '0', 'askNotional': '0'}
    """

    def __init__(self, json: dict):
        self.json = json

    @property
    def symbol(self) -> str:
        return self.json["symbol"]

    @property
    def initial_margin(self) -> Decimal:
        return Decimal(self.json["initialMargin"])

    @property
    def maint_margin(self) -> Decimal:
        return Decimal(self.json["maintMargin"])

    @property
    def unrealized_profit(self) -> Decimal:
        return Decimal(self.json["unrealizedProfit"])

    @property
    def position_initial_margin(self) -> Decimal:
        return Decimal(self.json["positionInitialMargin"])

    @property
    def open_order_initial_margin(self) -> Decimal:
        return Decimal(self.json["openOrderInitialMargin"])

    @property
    def leverage(self) -> Decimal:
        return Decimal(self.json["leverage"])

    @property
    def isolated(self) -> bool:
        return self.json["isolated"]

    @property
    def entry_price(self) -> Decimal:
        return Decimal(self.json["entryPrice"])

    @property
    def break_even_price(self) -> Decimal:
        return Decimal(self.json["breakEvenPrice"])

    @property
    def max_notional(self) -> Decimal:
        return Decimal(self.json["maxNotional"])

    @property
    def position_side(self) -> str:
        return self.json["positionSide"]

    @property
    def position_amount(self) -> Decimal:
        return Decimal(self.json["positionAmt"])

    @property
    def notional(self) -> Decimal:
        return Decimal(self.json["notional"])

    @property
    def isolated_wallet(self) -> Decimal:
        return Decimal(self.json["isolatedWallet"])

    @property
    def update_time(self) -> datetime.datetime:
        return helpers.timestamp_to_datetime(self.json["updateTime"])

    @property
    def bid_notional(self) -> Decimal:
        return Decimal(self.json["bidNotional"])

    @property
    def ask_notional(self) -> Decimal:
        return Decimal(self.json["askNotional"])


class FuturesAsset:
    def __init__(self, json: dict):
        self.json = json

    @property
    def asset(self) -> str:
        return self.json["asset"]

    @property
    def wallet_balance(self) -> Decimal:
        return Decimal(self.json["walletBalance"])

    @property
    def unrealized_profit(self) -> Decimal:
        return Decimal(self.json["unrealizedProfit"])

    @property
    def margin_balance(self) -> Decimal:
        return Decimal(self.json["marginBalance"])

    @property
    def maint_margin(self) -> Decimal:
        return Decimal(self.json["maintMargin"])

    @property
    def initial_margin(self) -> Decimal:
        return Decimal(self.json["initialMargin"])

    @property
    def position_initial_margin(self) -> Decimal:
        return Decimal(self.json["positionInitialMargin"])

    @property
    def open_order_initial_margin(self) -> Decimal:
        return Decimal(self.json["openOrderInitialMargin"])

    @property
    def max_withdraw_amount(self) -> Decimal:
        return Decimal(self.json["maxWithdrawAmount"])

    @property
    def cross_wallet_balance(self) -> Decimal:
        return Decimal(self.json["crossWalletBalance"])

    @property
    def cross_un_pnl(self) -> Decimal:
        return Decimal(self.json["crossUnPnl"])

    @property
    def available_balance(self) -> Decimal:
        return Decimal(self.json["availableBalance"])

    @property
    def margin_available(self) -> bool:
        return self.json["marginAvailable"]

    @property
    def update_time(self) -> datetime.datetime:
        return helpers.timestamp_to_datetime(self.json["updateTime"])


class FuturesBalance:
    def __init__(self, json: dict):
        self.json = json

    @property
    def fee_tier(self) -> int:
        return self.json["feeTier"]

    @property
    def can_trade(self) -> bool:
        return self.json["canTrade"]

    @property
    def can_deposit(self) -> bool:
        return self.json["canDeposit"]

    @property
    def can_withdraw(self) -> bool:
        return self.json["canWithdraw"]

    @property
    def trade_group_id(self) -> int:
        return self.json["tradeGroupId"]

    @property
    def update_time(self) -> datetime.datetime:
        return helpers.timestamp_to_datetime(self.json["updateTime"])

    @property
    def multi_assets_margin(self) -> bool:
        return self.json["multiAssetsMargin"]

    @property
    def total_initial_margin(self) -> Decimal:
        return Decimal(self.json["totalInitialMargin"])

    @property
    def total_maint_margin(self) -> Decimal:
        return Decimal(self.json["totalMaintMargin"])

    @property
    def total_wallet_balance(self) -> Decimal:
        return Decimal(self.json["totalWalletBalance"])

    @property
    def total_unrealized_profit(self) -> Decimal:
        return Decimal(self.json["totalUnrealizedProfit"])

    @property
    def total_margin_balance(self) -> Decimal:
        return Decimal(self.json["totalMarginBalance"])

    @property
    def total_position_initial_margin(self) -> Decimal:
        return Decimal(self.json["totalPositionInitialMargin"])

    @property
    def total_open_order_initial_margin(self) -> Decimal:
        return Decimal(self.json["totalOpenOrderInitialMargin"])

    @property
    def total_cross_wallet_balance(self) -> Decimal:
        return Decimal(self.json["totalCrossWalletBalance"])

    @property
    def total_cross_un_pnl(self) -> Decimal:
        return Decimal(self.json["totalCrossUnPnl"])

    @property
    def available_balance(self) -> Decimal:
        return Decimal(self.json["availableBalance"])

    @property
    def max_withdraw_amount(self) -> Decimal:
        return Decimal(self.json["maxWithdrawAmount"])

    @property
    def assets(self) -> Dict[str, FuturesAsset]:
        return {data["asset"]: FuturesAsset(data) for data in self.json["assets"]}

    @property
    def positions(self) -> Dict[str, Position]:
        return {data["symbol"]: Position(data) for data in self.json["positions"]}


class Trade:
    def __init__(self, json: dict):
        self.json = json

    @property
    def id(self) -> str:
        """The trade id."""
        return str(self.json["id"])

    @property
    def order_id(self) -> str:
        """The order id."""
        return str(self.json["orderId"])

    @property
    def datetime(self) -> datetime.datetime:
        return helpers.timestamp_to_datetime(self.json["time"])

    @property
    def is_best_match(self) -> bool:
        return self.json["isBestMatch"]

    @property
    def is_buyer(self) -> bool:
        return self.json["isBuyer"]

    @property
    def is_maker(self) -> bool:
        return self.json["isMaker"]

    @property
    def price(self) -> Decimal:
        return Decimal(self.json["price"])

    @property
    def amount(self) -> Decimal:
        return Decimal(self.json["qty"])

    @property
    def quote_amount(self) -> Decimal:
        return Decimal(self.json["quoteQty"])

    @property
    def commission(self) -> Decimal:
        return Decimal(self.json["commission"])

    @property
    def commission_asset(self) -> str:
        return self.json["commissionAsset"]


class OrderWrapper:
    def __init__(self, json: dict):
        self.json = json

    @property
    def id(self) -> str:
        """The order id."""
        return str(self.json["orderId"])

    @property
    def client_order_id(self) -> str:
        """The client order id."""
        return self.json["clientOrderId"]

    @property
    def order_list_id(self) -> Optional[str]:
        """The order list id."""
        ret = self.json.get("orderListId")
        ret = None if ret in [None, -1] else str(ret)
        return ret

    @property
    def status(self) -> str:
        """The status.

        Check **Order status** in https://binance-docs.github.io/apidocs/spot/en/#public-api-definitions.
        """
        return self.json["status"]

    @property
    def is_open(self) -> bool:
        """True if the order is open, False otherwise."""
        return helpers.order_status_is_open(self.status)

    @property
    def amount(self) -> Decimal:
        """The amount."""
        return Decimal(self.json["origQty"])

    @property
    def amount_filled(self) -> Decimal:
        """The amount filled."""
        return Decimal(self.json["executedQty"])

    @property
    def quote_amount_filled(self) -> Decimal:
        """The amount filled in quote units."""
        return Decimal(self.json["cummulativeQuoteQty"])

    @property
    def limit_price(self) -> Optional[Decimal]:
        """The limit price."""
        return helpers.get_optional_decimal(self.json, "price", True)

    @property
    def stop_price(self) -> Optional[Decimal]:
        """The stop price."""
        return helpers.get_optional_decimal(self.json, "stopPrice", True)

    @property
    def time_in_force(self) -> Optional[str]:
        """The time in force.

        Check **Time in force** in https://binance-docs.github.io/apidocs/spot/en/#public-api-definitions.
        """
        return self.json.get("timeInForce")


class OrderInfo(OrderWrapper):
    def __init__(self, json: dict, trades: Sequence[Trade]):
        super().__init__(json)
        self.trades = trades
        self._fees: Dict[str, Decimal] = collections.defaultdict(Decimal)
        for trade in trades:
            if trade.commission:
                self._fees[trade.commission_asset] += trade.commission

    @property
    def amount_remaining(self) -> Decimal:
        """The amount remaining to be filled."""
        return self.amount - self.amount_filled

    @property
    def fill_price(self) -> Optional[Decimal]:
        """The fill price."""
        ret = None
        if self.amount_filled:
            ret = self.quote_amount_filled / self.amount_filled
        return ret

    @property
    def fees(self) -> Dict[str, Decimal]:
        """The fees."""
        return self._fees


class Fill:
    def __init__(self, json: dict):
        self.json = json

    @property
    def price(self) -> Decimal:
        """The price."""
        return Decimal(self.json["price"])

    @property
    def amount(self) -> Decimal:
        """The amount."""
        return Decimal(self.json["qty"])

    @property
    def commission(self) -> Decimal:
        """The commission."""
        return Decimal(self.json["commission"])

    @property
    def commission_asset(self) -> str:
        """The commission asset."""
        return self.json["commissionAsset"]


class CreatedOrder:
    def __init__(self, json: dict):
        self.json = json

    @property
    def id(self) -> str:
        """The order id."""
        return str(self.json["orderId"])

    @property
    def datetime(self) -> datetime.datetime:
        """The creation datetime."""
        return helpers.timestamp_to_datetime(self.json["transactTime"])

    @property
    def client_order_id(self) -> str:
        """The client order id."""
        return self.json["clientOrderId"]

    @property
    def limit_price(self) -> Optional[Decimal]:
        """The limit price.

        Only available for RESULT / FULL responses.
        """
        return helpers.get_optional_decimal(self.json, "price", True)

    @property
    def amount(self) -> Optional[Decimal]:
        """The amount.

        Only available for RESULT / FULL responses.
        """
        return helpers.get_optional_decimal(self.json, "origQty", False)

    @property
    def amount_filled(self) -> Optional[Decimal]:
        """The amount filled.

        Only available for RESULT / FULL responses.
        """
        return helpers.get_optional_decimal(self.json, "executedQty", False)

    @property
    def quote_amount_filled(self) -> Optional[Decimal]:
        """The amount filled in quote units.

        Only available for RESULT / FULL responses.
        """
        return helpers.get_optional_decimal(self.json, "cummulativeQuoteQty", False)

    @property
    def status(self) -> Optional[str]:
        """The status.

        Only available for RESULT / FULL responses.
        """
        return self.json.get("status")

    @property
    def time_in_force(self) -> Optional[str]:
        """The time in force.

        Only available for RESULT / FULL responses.
        """
        return self.json.get("timeInForce")

    @property
    def is_open(self) -> bool:
        """True if the order is open, False otherwise.

        Only available for RESULT / FULL responses.
        """
        assert self.status is not None, "status not set"
        return helpers.order_status_is_open(self.status)


class CanceledOrder(OrderWrapper):
    @property
    def operation(self) -> OrderOperation:
        """The operation."""
        return helpers.side_to_order_operation(self.json["side"])

    @property
    def type(self) -> str:
        """The type of order.

        Check **Order types** in https://binance-docs.github.io/apidocs/spot/en/#public-api-definitions.
        """
        return self.json["type"]


class OpenOrder(OrderWrapper):
    @property
    def datetime(self) -> datetime.datetime:
        """The creation datetime."""
        return helpers.timestamp_to_datetime(self.json["time"])

    @property
    def operation(self) -> OrderOperation:
        """The operation."""
        return helpers.side_to_order_operation(self.json["side"])

    @property
    def type(self) -> str:
        """The type of order.

        Check **Order types** in https://binance-docs.github.io/apidocs/spot/en/#public-api-definitions.
        """
        return self.json["type"]


class OCOOrderWrapper:
    def __init__(self, json: dict):
        self.json = json

    @property
    def order_list_id(self) -> str:
        """The order list id."""
        return str(self.json["orderListId"])

    @property
    def client_order_list_id(self) -> str:
        """A client id for the order list."""
        return str(self.json["listClientOrderId"])

    @property
    def datetime(self) -> datetime.datetime:
        """The creation datetime."""
        return helpers.timestamp_to_datetime(self.json["transactionTime"])

    @property
    def is_open(self) -> bool:
        """True if the order is open, False otherwise."""
        return helpers.oco_order_status_is_open(self.json["listOrderStatus"])

    @property
    def limit_order_id(self) -> str:
        """The id for the limit order."""
        order_ids = [
            str(order["orderId"])
            for order in self.json.get("orderReports", [])
            if order["type"] in ("LIMIT", "LIMIT_MAKER")
        ]
        return order_ids[0]

    @property
    def stop_loss_order_id(self) -> str:
        """The id for the stop loss order."""
        order_ids = [
            str(order["orderId"])
            for order in self.json.get("orderReports", [])
            if order["type"] in ("STOP_LOSS", "STOP_LOSS_LIMIT")
        ]
        return order_ids[0]


class CreatedOCOOrder(OCOOrderWrapper):
    pass


class OCOOrderInfo(OCOOrderWrapper):
    pass


class CanceledOCOOrder(OCOOrderWrapper):
    pass
