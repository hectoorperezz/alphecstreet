"""Tests for IBKR order executor."""

from decimal import Decimal
import pandas as pd
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from execution.executor import IBKROrderExecutor, RiskCheckError, OrderRejectedError
from execution.connection import IBKRConnectionManager
from execution.models import (
    OrderRequest,
    Order,
    Fill,
    Position,
    OrderType,
    Side,
    TimeInForce,
    OrderStatus,
)


@pytest.mark.unit
class TestOrderExecutor:
    """Test order executor functionality."""

    @pytest.fixture
    def mock_connection_manager(self) -> MagicMock:
        """Create a mock connection manager."""
        manager = MagicMock(spec=IBKRConnectionManager)
        manager.is_connected.return_value = True
        manager.ensure_connected = AsyncMock()
        return manager

    @pytest.fixture
    def executor(self, mock_connection_manager: MagicMock) -> IBKROrderExecutor:
        """Create an executor with mocked connection."""
        return IBKROrderExecutor(connection_manager=mock_connection_manager)

    @pytest.mark.asyncio
    async def test_submit_market_order(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test submitting a market order."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            client_order_id="test-order-001",
        )
        
        with patch.object(executor, "_place_order_with_ib") as mock_place:
            mock_order = Order(
                order_id="12345",
                client_order_id="test-order-001",
                symbol="AAPL",
                quantity=Decimal("100"),
                order_type=OrderType.MARKET,
                side=Side.BUY,
                limit_price=None,
                stop_price=None,
                status=OrderStatus.SUBMITTED,
                submitted_at=pd.Timestamp.now(tz="UTC"),
            )
            mock_place.return_value = mock_order
            
            order = await executor.submit_order(request)
            
            assert order.symbol == "AAPL"
            assert order.quantity == Decimal("100")
            assert order.order_type == OrderType.MARKET
            assert order.status == OrderStatus.SUBMITTED
            mock_connection_manager.ensure_connected.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_limit_order(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test submitting a limit order."""
        request = OrderRequest(
            symbol="TSLA",
            quantity=Decimal("50"),
            order_type=OrderType.LIMIT,
            side=Side.SELL,
            limit_price=Decimal("250.50"),
        )
        
        with patch.object(executor, "_place_order_with_ib") as mock_place:
            mock_order = Order(
                order_id="67890",
                client_order_id=None,
                symbol="TSLA",
                quantity=Decimal("50"),
                order_type=OrderType.LIMIT,
                side=Side.SELL,
                limit_price=Decimal("250.50"),
                stop_price=None,
                status=OrderStatus.SUBMITTED,
                submitted_at=pd.Timestamp.now(tz="UTC"),
            )
            mock_place.return_value = mock_order
            
            order = await executor.submit_order(request)
            
            assert order.limit_price == Decimal("250.50")
            assert order.side == Side.SELL

    @pytest.mark.asyncio
    async def test_submit_order_when_disconnected(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test that order submission fails when disconnected."""
        mock_connection_manager.is_connected.return_value = False
        mock_connection_manager.ensure_connected.side_effect = ConnectionError("Not connected")
        
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        with pytest.raises(ConnectionError):
            await executor.submit_order(request)

    @pytest.mark.asyncio
    async def test_submit_order_with_risk_check_approved(
        self, mock_connection_manager: MagicMock
    ) -> None:
        """Test order submission with risk check approval."""
        risk_check = MagicMock(return_value=True)
        executor = IBKROrderExecutor(
            connection_manager=mock_connection_manager,
            risk_check_callback=risk_check,
        )
        
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        with patch.object(executor, "_place_order_with_ib") as mock_place:
            mock_order = Order(
                order_id="12345",
                client_order_id=None,
                symbol="AAPL",
                quantity=Decimal("100"),
                order_type=OrderType.MARKET,
                side=Side.BUY,
                limit_price=None,
                stop_price=None,
                status=OrderStatus.SUBMITTED,
                submitted_at=pd.Timestamp.now(tz="UTC"),
            )
            mock_place.return_value = mock_order
            
            order = await executor.submit_order(request)
            
            risk_check.assert_called_once_with(request)
            assert order.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_submit_order_with_risk_check_rejected(
        self, mock_connection_manager: MagicMock
    ) -> None:
        """Test order submission with risk check rejection."""
        risk_check = MagicMock(return_value=False)
        executor = IBKROrderExecutor(
            connection_manager=mock_connection_manager,
            risk_check_callback=risk_check,
        )
        
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("10000"),  # Too large
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        with pytest.raises(RiskCheckError):
            await executor.submit_order(request)
        
        risk_check.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_cancel_order(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test cancelling an order."""
        order_id = "12345"
        
        with patch.object(executor, "_cancel_order_with_ib") as mock_cancel:
            mock_cancel.return_value = None
            
            await executor.cancel_order(order_id)
            
            mock_cancel.assert_called_once_with(order_id)
            mock_connection_manager.ensure_connected.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_order_status(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test querying order status."""
        order_id = "12345"
        
        with patch.object(executor, "_get_order_from_ib") as mock_get:
            mock_order = Order(
                order_id="12345",
                client_order_id=None,
                symbol="AAPL",
                quantity=Decimal("100"),
                order_type=OrderType.MARKET,
                side=Side.BUY,
                limit_price=None,
                stop_price=None,
                status=OrderStatus.FILLED,
                submitted_at=pd.Timestamp.now(tz="UTC"),
                filled_quantity=Decimal("100"),
                average_fill_price=Decimal("151.25"),
            )
            mock_get.return_value = mock_order
            
            order = await executor.get_order_status(order_id)
            
            assert order.order_id == "12345"
            assert order.status == OrderStatus.FILLED
            assert order.filled_quantity == Decimal("100")

    @pytest.mark.asyncio
    async def test_get_open_orders(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test retrieving all open orders."""
        with patch.object(executor, "_get_open_orders_from_ib") as mock_get:
            mock_orders = [
                Order(
                    order_id="12345",
                    client_order_id=None,
                    symbol="AAPL",
                    quantity=Decimal("100"),
                    order_type=OrderType.LIMIT,
                    side=Side.BUY,
                    limit_price=Decimal("150.00"),
                    stop_price=None,
                    status=OrderStatus.SUBMITTED,
                    submitted_at=pd.Timestamp.now(tz="UTC"),
                ),
                Order(
                    order_id="67890",
                    client_order_id=None,
                    symbol="TSLA",
                    quantity=Decimal("50"),
                    order_type=OrderType.LIMIT,
                    side=Side.SELL,
                    limit_price=Decimal("250.00"),
                    stop_price=None,
                    status=OrderStatus.SUBMITTED,
                    submitted_at=pd.Timestamp.now(tz="UTC"),
                ),
            ]
            mock_get.return_value = mock_orders
            
            orders = await executor.get_open_orders()
            
            assert len(orders) == 2
            assert orders[0].symbol == "AAPL"
            assert orders[1].symbol == "TSLA"

    @pytest.mark.asyncio
    async def test_get_positions(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test retrieving current positions."""
        with patch.object(executor, "_get_positions_from_ib") as mock_get:
            mock_positions = [
                Position(
                    symbol="AAPL",
                    quantity=Decimal("100"),
                    average_cost=Decimal("150.00"),
                    market_value=Decimal("15100.00"),
                    unrealized_pnl=Decimal("100.00"),
                    timestamp=pd.Timestamp.now(tz="UTC"),
                ),
                Position(
                    symbol="TSLA",
                    quantity=Decimal("-50"),  # Short
                    average_cost=Decimal("250.00"),
                    market_value=Decimal("-12400.00"),
                    unrealized_pnl=Decimal("100.00"),
                    timestamp=pd.Timestamp.now(tz="UTC"),
                ),
            ]
            mock_get.return_value = mock_positions
            
            positions = await executor.get_positions()
            
            assert len(positions) == 2
            assert positions[0].quantity > 0  # Long
            assert positions[1].quantity < 0  # Short

    @pytest.mark.asyncio
    async def test_order_rejected_by_broker(
        self, executor: IBKROrderExecutor, mock_connection_manager: MagicMock
    ) -> None:
        """Test handling broker rejection of order."""
        request = OrderRequest(
            symbol="INVALID",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        with patch.object(executor, "_place_order_with_ib") as mock_place:
            mock_place.side_effect = OrderRejectedError("Invalid symbol")
            
            with pytest.raises(OrderRejectedError) as exc_info:
                await executor.submit_order(request)
            
            assert "Invalid symbol" in str(exc_info.value)


@pytest.mark.integration
class TestOrderExecutorIntegration:
    """Integration tests requiring TWS connection."""

    @pytest.fixture
    async def real_executor(self) -> IBKROrderExecutor:
        """Create executor with real TWS connection."""
        manager = IBKRConnectionManager(port=7497)  # Paper trading
        try:
            await manager.connect()
        except ConnectionError:
            pytest.skip("TWS not available")
        
        executor = IBKROrderExecutor(connection_manager=manager)
        yield executor
        
        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_submit_and_cancel_order(self, real_executor: IBKROrderExecutor) -> None:
        """Test submitting and cancelling an order with real TWS."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("1"),  # Small quantity for testing
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            limit_price=Decimal("1.00"),  # Far from market to avoid fill
        )
        
        order = await real_executor.submit_order(request)
        assert order.order_id is not None
        assert order.status in [OrderStatus.SUBMITTED, OrderStatus.PENDING]
        
        await real_executor.cancel_order(order.order_id)
        
        # Verify cancellation
        updated_order = await real_executor.get_order_status(order.order_id)
        assert updated_order.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_get_positions_from_real_account(
        self, real_executor: IBKROrderExecutor
    ) -> None:
        """Test retrieving positions from real account."""
        positions = await real_executor.get_positions()
        
        # Just verify it returns a list (may be empty)
        assert isinstance(positions, list)
        
        # If there are positions, verify structure
        for position in positions:
            assert isinstance(position.symbol, str)
            assert isinstance(position.quantity, Decimal)
            assert position.timestamp.tz is not None

