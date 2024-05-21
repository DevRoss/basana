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
from typing import Any, Dict, Optional
import abc

from . import helpers
from basana.core.enums import OrderOperation
from basana.core.pair import Pair, FuturesPair


class ExchangeOrder(metaclass=abc.ABCMeta):
    def __init__(
            self, operation: OrderOperation, pair: FuturesPair, amount: Optional[Decimal],
            client_order_id: Optional[str] = None, **kwargs: Dict[str, Any]
    ):
        self._operation = operation
        self._pair = pair
        self._amount = amount
        self._client_order_id = client_order_id
        self._kwargs = kwargs

    @abc.abstractmethod
    async def create_order(self, futures_account_cli) -> dict:
        raise NotImplementedError()


class MarketOrder(ExchangeOrder):
    def __init__(
            self, operation: OrderOperation, pair: FuturesPair, amount: Decimal,
            client_order_id: Optional[str] = None, **kwargs: Dict[str, Any]
    ):
        super().__init__(operation, pair, amount, client_order_id=client_order_id, **kwargs)

    async def create_order(self, futures_account_cli) -> dict:
        return await futures_account_cli.create_order(
            helpers.pair_to_order_book_symbol(self._pair), helpers.order_operation_to_side(self._operation), "MARKET",
            quantity=self._amount, new_client_order_id=self._client_order_id,
            **self._kwargs
        )


class LimitOrder(ExchangeOrder):
    def __init__(
            self, operation: OrderOperation, pair: FuturesPair, amount: Decimal, limit_price: Decimal,
            time_in_force: str = "GTC", client_order_id: Optional[str] = None, **kwargs: Dict[str, Any]
    ):
        super().__init__(operation, pair, amount, client_order_id=client_order_id, **kwargs)
        self._limit_price = limit_price
        self._time_in_force = time_in_force

    async def create_order(self, futures_account_cli) -> dict:
        return await futures_account_cli.create_order(
            helpers.pair_to_order_book_symbol(self._pair), helpers.order_operation_to_side(self._operation), "LIMIT",
            quantity=self._amount, price=self._limit_price, time_in_force=self._time_in_force,
            new_client_order_id=self._client_order_id, **self._kwargs
        )


class StopLimitOrder(ExchangeOrder):
    def __init__(
            self, operation: OrderOperation, pair: FuturesPair, amount: Decimal, stop_price: Decimal, limit_price: Decimal,
            time_in_force: str = "GTC", client_order_id: Optional[str] = None, **kwargs: Dict[str, Any]
    ):
        super().__init__(operation, pair, amount, client_order_id=client_order_id, **kwargs)
        self._stop_price = stop_price
        self._limit_price = limit_price
        self._time_in_force = time_in_force

    async def create_order(self, futures_account_cli) -> dict:
        return await futures_account_cli.create_order(
            helpers.pair_to_order_book_symbol(self._pair), helpers.order_operation_to_side(self._operation),
            "STOP", quantity=self._amount, stop_price=self._stop_price, price=self._limit_price,
            time_in_force=self._time_in_force, new_client_order_id=self._client_order_id, **self._kwargs
        )
