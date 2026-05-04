from enum import Enum
from pydantic import BaseModel
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    IOC = "IOC"
    FOK = "FOK"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class OrderRequest(BaseModel):
    client_order_id: Optional[str] = None  # idempotency key
    symbol: str
    side: Side
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: Optional[str] = None
    strategy: Optional[str] = "AGGRESSIVE"  # routing hint


class Order(BaseModel):
    order_id: str
    request: OrderRequest
    status: OrderStatus = OrderStatus.NEW
    filled_qty: float = 0.0
    remaining_qty: float = 0.0


class FillEvent(BaseModel):
    order_id: str
    filled_qty: float
    fill_price: float
    fee: float
    timestamp: float
