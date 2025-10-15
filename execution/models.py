"""Data models for order execution."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

import pandas as pd


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class Side(str, Enum):
    """Order side enumeration."""

    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(str, Enum):
    """Time in force enumeration."""

    DAY = "DAY"  # Day order
    GTC = "GTC"  # Good till cancelled
    IOC = "IOC"  # Immediate or cancel
    FOK = "FOK"  # Fill or kill


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "PENDING"  # Order created but not yet submitted
    SUBMITTED = "SUBMITTED"  # Order submitted to broker
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Order partially executed
    FILLED = "FILLED"  # Order completely filled
    CANCELLED = "CANCELLED"  # Order cancelled
    REJECTED = "REJECTED"  # Order rejected by broker


@dataclass(frozen=True)
class OrderRequest:
    """
    Request to submit an order.

    Attributes:
        symbol: Ticker symbol (e.g., "AAPL")
        quantity: Order quantity (must be Decimal for precision)
        order_type: Type of order (MARKET, LIMIT, STOP, STOP_LIMIT)
        side: BUY or SELL
        limit_price: Limit price for LIMIT and STOP_LIMIT orders
        stop_price: Stop price for STOP and STOP_LIMIT orders
        time_in_force: Order duration (DAY, GTC, IOC, FOK)
        account: Optional account identifier
        client_order_id: Optional client-side order ID for correlation

    Examples:
        >>> # Market order
        >>> OrderRequest(
        ...     symbol="AAPL",
        ...     quantity=Decimal("100"),
        ...     order_type=OrderType.MARKET,
        ...     side=Side.BUY
        ... )
        
        >>> # Limit order
        >>> OrderRequest(
        ...     symbol="TSLA",
        ...     quantity=Decimal("50"),
        ...     order_type=OrderType.LIMIT,
        ...     side=Side.SELL,
        ...     limit_price=Decimal("250.50")
        ... )
    """

    symbol: str
    quantity: Decimal
    order_type: OrderType
    side: Side
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    account: Optional[str] = None
    client_order_id: Optional[str] = None


@dataclass(frozen=True)
class Order:
    """
    Submitted order with broker assignment.

    Attributes:
        order_id: Broker-assigned order ID
        client_order_id: Optional client-side order ID for correlation
        symbol: Ticker symbol
        quantity: Total order quantity
        order_type: Type of order
        side: BUY or SELL
        limit_price: Limit price if applicable
        stop_price: Stop price if applicable
        status: Current order status
        submitted_at: UTC timestamp when order was submitted
        filled_quantity: Quantity filled so far
        average_fill_price: Average price of fills (if any)
    """

    order_id: str
    client_order_id: Optional[str]
    symbol: str
    quantity: Decimal
    order_type: OrderType
    side: Side
    limit_price: Optional[Decimal]
    stop_price: Optional[Decimal]
    status: OrderStatus
    submitted_at: pd.Timestamp  # Must be UTC
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Optional[Decimal] = None


@dataclass(frozen=True)
class Fill:
    """
    Execution fill event.

    Attributes:
        fill_id: Unique fill identifier
        order_id: Associated order ID
        symbol: Ticker symbol
        quantity: Fill quantity
        price: Execution price
        side: BUY or SELL
        timestamp: UTC timestamp of fill
        commission: Commission charged (if available)
    """

    fill_id: str
    order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    side: Side
    timestamp: pd.Timestamp  # Must be UTC
    commission: Optional[Decimal] = None


@dataclass(frozen=True)
class Position:
    """
    Current position snapshot.

    Attributes:
        symbol: Ticker symbol
        quantity: Position quantity (positive=long, negative=short)
        average_cost: Average cost basis
        market_value: Current market value
        unrealized_pnl: Unrealized profit/loss
        timestamp: UTC timestamp of snapshot
    """

    symbol: str
    quantity: Decimal  # Positive = long, negative = short
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    timestamp: pd.Timestamp  # Must be UTC

