from enum import Enum, unique


@unique
class BinanceContractType(Enum):
    """
    Represents a `Binance` contract type.
    """

    PERPETUAL = "PERPETUAL"
    CURRENT_MONTH = "CURRENT_MONTH"
    NEXT_MONTH = "NEXT_MONTH"
    CURRENT_QUARTER = "CURRENT_QUARTER"
    NEXT_QUARTER = "NEXT_QUARTER"
    PERPETUAL_DELIVERING = "PERPETUAL_DELIVERING"

    @property
    def is_perpetual(self):
        return self == BinanceContractType.PERPETUAL

    @property
    def is_delivery(self):
        return self in (
            BinanceContractType.CURRENT_MONTH,
            BinanceContractType.NEXT_MONTH,
            BinanceContractType.CURRENT_QUARTER,
            BinanceContractType.NEXT_QUARTER,
            BinanceContractType.PERPETUAL_DELIVERING,
        )
