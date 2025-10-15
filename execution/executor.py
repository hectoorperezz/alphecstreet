"""IBKR order executor - main interface for order operations."""

import logging
from decimal import Decimal
from typing import Any, Callable, List, Optional

import pandas as pd
from ib_insync import IB, Contract, LimitOrder, MarketOrder, Order as IBOrder, StopOrder

from execution.audit import AuditLogger
from execution.connection import IBKRConnectionManager, ConnectionError
from execution.models import (
    Fill,
    Order,
    OrderRequest,
    OrderStatus,
    OrderType,
    Position,
    Side,
    TimeInForce,
)


logger = logging.getLogger(__name__)


class RiskCheckError(Exception):
    """Exception raised when risk check rejects an order."""

    pass


class OrderRejectedError(Exception):
    """Exception raised when broker rejects an order."""

    pass


class IBKROrderExecutor:
    """
    High-level interface for order execution.

    This class provides a clean API for submitting orders, cancelling orders,
    and querying order/position status. It handles conversion between domain
    models and ib_insync objects, enforces risk checks, and maintains audit logs.

    Examples:
        >>> manager = IBKRConnectionManager(port=7497)
        >>> await manager.connect()
        >>> executor = IBKROrderExecutor(connection_manager=manager)
        >>> 
        >>> request = OrderRequest(
        ...     symbol="AAPL",
        ...     quantity=Decimal("100"),
        ...     order_type=OrderType.MARKET,
        ...     side=Side.BUY
        ... )
        >>> order = await executor.submit_order(request)
        >>> print(f"Order {order.order_id} submitted")
    """

    def __init__(
        self,
        connection_manager: IBKRConnectionManager,
        risk_check_callback: Optional[Callable[[OrderRequest], bool]] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize with connection manager and optional risk checks.

        Args:
            connection_manager: Manages TWS connection
            risk_check_callback: Optional function to validate orders before submission.
                                Should return True to approve, False to reject.
            audit_logger: Optional audit logger (creates default if not provided)
        """
        self.connection_manager = connection_manager
        self.risk_check_callback = risk_check_callback
        self.audit_logger = audit_logger or AuditLogger()

    async def submit_order(self, request: OrderRequest) -> Order:
        """
        Submit an order to IBKR.

        Args:
            request: The order request

        Returns:
            The submitted order with broker-assigned ID

        Raises:
            RiskCheckError: If risk check callback rejects order
            ConnectionError: If not connected to TWS
            OrderRejectedError: If IBKR rejects the order
        """
        # Run risk check if configured
        if self.risk_check_callback is not None:
            if not self.risk_check_callback(request):
                error_msg = f"Risk check rejected order for {request.symbol}"
                self.audit_logger.log_risk_check_failure(request, error_msg)
                raise RiskCheckError(error_msg)

        # Ensure connection
        await self.connection_manager.ensure_connected()

        # Place order with IB
        try:
            order = await self._place_order_with_ib(request)
            self.audit_logger.log_order_submitted(request, order)
            logger.info(
                f"Order submitted: {order.order_id} - {request.side.value} "
                f"{request.quantity} {request.symbol} @ {request.order_type.value}"
            )
            return order
        except Exception as e:
            logger.error(f"Failed to submit order for {request.symbol}: {e}")
            raise OrderRejectedError(f"Order rejected by broker: {e}") from e

    async def cancel_order(self, order_id: str) -> None:
        """
        Cancel an open order.

        Args:
            order_id: The broker-assigned order ID

        Raises:
            ConnectionError: If not connected to TWS
        """
        await self.connection_manager.ensure_connected()
        await self._cancel_order_with_ib(order_id)
        self.audit_logger.log_order_cancelled(order_id, "User requested cancellation")
        logger.info(f"Order cancelled: {order_id}")

    async def get_order_status(self, order_id: str) -> Order:
        """
        Query current order status.

        Args:
            order_id: The broker-assigned order ID

        Returns:
            The order with current status

        Raises:
            ConnectionError: If not connected to TWS
        """
        await self.connection_manager.ensure_connected()
        return await self._get_order_from_ib(order_id)

    async def get_open_orders(self) -> List[Order]:
        """
        Retrieve all open orders.

        Returns:
            List of open orders

        Raises:
            ConnectionError: If not connected to TWS
        """
        await self.connection_manager.ensure_connected()
        return await self._get_open_orders_from_ib()

    async def get_positions(self) -> List[Position]:
        """
        Retrieve current positions.

        Returns:
            List of current positions

        Raises:
            ConnectionError: If not connected to TWS
        """
        await self.connection_manager.ensure_connected()
        return await self._get_positions_from_ib()

    # Internal methods for IB interaction

    async def _place_order_with_ib(self, request: OrderRequest) -> Order:
        """Convert OrderRequest to IB order and place it."""
        ib = self.connection_manager.get_ib_client()

        # Create contract
        contract = Contract()
        contract.symbol = request.symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        # Create IB order based on type
        ib_order = self._create_ib_order(request)

        # Place order
        trade = ib.placeOrder(contract, ib_order)
        await ib.sleepAsync(0.5)  # Give time for order to be acknowledged

        # Convert to domain model
        return self._convert_to_order(trade, request)

    def _create_ib_order(self, request: OrderRequest) -> IBOrder:
        """Create ib_insync Order from OrderRequest."""
        if request.order_type == OrderType.MARKET:
            ib_order = MarketOrder(
                action=request.side.value,
                totalQuantity=float(request.quantity),
            )
        elif request.order_type == OrderType.LIMIT:
            if request.limit_price is None:
                raise ValueError("Limit price required for LIMIT order")
            ib_order = LimitOrder(
                action=request.side.value,
                totalQuantity=float(request.quantity),
                lmtPrice=float(request.limit_price),
            )
        elif request.order_type == OrderType.STOP:
            if request.stop_price is None:
                raise ValueError("Stop price required for STOP order")
            ib_order = StopOrder(
                action=request.side.value,
                totalQuantity=float(request.quantity),
                stopPrice=float(request.stop_price),
            )
        elif request.order_type == OrderType.STOP_LIMIT:
            if request.stop_price is None or request.limit_price is None:
                raise ValueError("Stop and limit prices required for STOP_LIMIT order")
            # Note: ib_insync doesn't have a dedicated StopLimitOrder class
            # We create a LimitOrder with auxPrice as the stop trigger
            ib_order = LimitOrder(
                action=request.side.value,
                totalQuantity=float(request.quantity),
                lmtPrice=float(request.limit_price),
            )
            ib_order.auxPrice = float(request.stop_price)
        else:
            raise ValueError(f"Unsupported order type: {request.order_type}")

        # Set time in force
        if request.time_in_force == TimeInForce.DAY:
            ib_order.tif = "DAY"
        elif request.time_in_force == TimeInForce.GTC:
            ib_order.tif = "GTC"
        elif request.time_in_force == TimeInForce.IOC:
            ib_order.tif = "IOC"
        elif request.time_in_force == TimeInForce.FOK:
            ib_order.tif = "FOK"

        # Set account if specified
        if request.account:
            ib_order.account = request.account

        return ib_order

    def _convert_to_order(self, trade: Any, request: OrderRequest) -> Order:
        """Convert ib_insync Trade to domain Order model."""
        order_status = self._map_ib_status(trade.orderStatus.status)

        return Order(
            order_id=str(trade.order.orderId),
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            quantity=request.quantity,
            order_type=request.order_type,
            side=request.side,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            status=order_status,
            submitted_at=pd.Timestamp.now(tz="UTC"),
            filled_quantity=Decimal(str(trade.orderStatus.filled)),
            average_fill_price=(
                Decimal(str(trade.orderStatus.avgFillPrice))
                if trade.orderStatus.avgFillPrice > 0
                else None
            ),
        )

    def _map_ib_status(self, ib_status: str) -> OrderStatus:
        """Map IB order status to domain OrderStatus."""
        status_map = {
            "PendingSubmit": OrderStatus.PENDING,
            "Submitted": OrderStatus.SUBMITTED,
            "PreSubmitted": OrderStatus.SUBMITTED,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Rejected": OrderStatus.REJECTED,
            "Inactive": OrderStatus.REJECTED,
        }
        return status_map.get(ib_status, OrderStatus.PENDING)

    async def _cancel_order_with_ib(self, order_id: str) -> None:
        """Cancel order through IB."""
        ib = self.connection_manager.get_ib_client()
        # Find the trade by order ID
        for trade in ib.trades():
            if str(trade.order.orderId) == order_id:
                ib.cancelOrder(trade.order)
                return
        raise ValueError(f"Order {order_id} not found")

    async def _get_order_from_ib(self, order_id: str) -> Order:
        """Get order status from IB."""
        ib = self.connection_manager.get_ib_client()
        for trade in ib.trades():
            if str(trade.order.orderId) == order_id:
                # Reconstruct order from trade
                return self._convert_trade_to_order(trade)
        raise ValueError(f"Order {order_id} not found")

    async def _get_open_orders_from_ib(self) -> List[Order]:
        """Get all open orders from IB."""
        ib = self.connection_manager.get_ib_client()
        orders = []
        for trade in ib.openTrades():
            orders.append(self._convert_trade_to_order(trade))
        return orders

    async def _get_positions_from_ib(self) -> List[Position]:
        """Get all positions from IB."""
        ib = self.connection_manager.get_ib_client()
        positions = []
        for position in ib.positions():
            positions.append(
                Position(
                    symbol=position.contract.symbol,
                    quantity=Decimal(str(position.position)),
                    average_cost=Decimal(str(position.avgCost)),
                    market_value=Decimal(str(position.position * position.avgCost)),
                    unrealized_pnl=Decimal("0"),  # Would need market data to calculate
                    timestamp=pd.Timestamp.now(tz="UTC"),
                )
            )
        return positions

    def _convert_trade_to_order(self, trade: Any) -> Order:
        """Convert ib_insync Trade to domain Order (for status queries)."""
        ib_order = trade.order
        order_status = self._map_ib_status(trade.orderStatus.status)

        # Determine order type and side
        order_type = self._determine_order_type(ib_order)
        side = Side.BUY if ib_order.action == "BUY" else Side.SELL

        return Order(
            order_id=str(ib_order.orderId),
            client_order_id=None,  # Not stored in IB order
            symbol=trade.contract.symbol,
            quantity=Decimal(str(ib_order.totalQuantity)),
            order_type=order_type,
            side=side,
            limit_price=(
                Decimal(str(ib_order.lmtPrice)) if ib_order.lmtPrice > 0 else None
            ),
            stop_price=(
                Decimal(str(ib_order.auxPrice)) if ib_order.auxPrice > 0 else None
            ),
            status=order_status,
            submitted_at=pd.Timestamp.now(tz="UTC"),  # IB doesn't provide submission time
            filled_quantity=Decimal(str(trade.orderStatus.filled)),
            average_fill_price=(
                Decimal(str(trade.orderStatus.avgFillPrice))
                if trade.orderStatus.avgFillPrice > 0
                else None
            ),
        )

    def _determine_order_type(self, ib_order: IBOrder) -> OrderType:
        """Determine OrderType from ib_insync Order."""
        if isinstance(ib_order, MarketOrder):
            return OrderType.MARKET
        elif isinstance(ib_order, LimitOrder):
            if ib_order.auxPrice > 0:
                return OrderType.STOP_LIMIT
            return OrderType.LIMIT
        elif isinstance(ib_order, StopOrder):
            return OrderType.STOP
        else:
            return OrderType.MARKET  # Default

