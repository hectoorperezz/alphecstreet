"""Tests for execution data models."""

from decimal import Decimal
import pandas as pd
import pytest

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
class TestOrderRequest:
    """Test OrderRequest data model."""

    def test_create_market_order_request(self) -> None:
        """Test creating a market order request."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        assert request.symbol == "AAPL"
        assert request.quantity == Decimal("100")
        assert request.order_type == OrderType.MARKET
        assert request.side == Side.BUY
        assert request.limit_price is None
        assert request.stop_price is None
        assert request.time_in_force == TimeInForce.DAY

    def test_create_limit_order_request(self) -> None:
        """Test creating a limit order request."""
        request = OrderRequest(
            symbol="TSLA",
            quantity=Decimal("50"),
            order_type=OrderType.LIMIT,
            side=Side.SELL,
            limit_price=Decimal("250.50"),
            time_in_force=TimeInForce.GTC,
        )
        
        assert request.symbol == "TSLA"
        assert request.limit_price == Decimal("250.50")
        assert request.time_in_force == TimeInForce.GTC

    def test_create_stop_order_request(self) -> None:
        """Test creating a stop order request."""
        request = OrderRequest(
            symbol="SPY",
            quantity=Decimal("200"),
            order_type=OrderType.STOP,
            side=Side.SELL,
            stop_price=Decimal("400.00"),
        )
        
        assert request.stop_price == Decimal("400.00")
        assert request.limit_price is None

    def test_create_stop_limit_order_request(self) -> None:
        """Test creating a stop-limit order request."""
        request = OrderRequest(
            symbol="QQQ",
            quantity=Decimal("100"),
            order_type=OrderType.STOP_LIMIT,
            side=Side.BUY,
            stop_price=Decimal("350.00"),
            limit_price=Decimal("351.00"),
        )
        
        assert request.stop_price == Decimal("350.00")
        assert request.limit_price == Decimal("351.00")

    def test_order_request_immutable(self) -> None:
        """Test that OrderRequest is immutable."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        with pytest.raises(AttributeError):
            request.quantity = Decimal("200")  # type: ignore

    def test_quantity_is_decimal(self) -> None:
        """Test that quantity must be Decimal for precision."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100.5"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        assert isinstance(request.quantity, Decimal)
        # Verify precision is maintained
        assert request.quantity == Decimal("100.5")


@pytest.mark.unit
class TestOrder:
    """Test Order data model."""

    def test_create_order(self) -> None:
        """Test creating an order."""
        timestamp = pd.Timestamp.now(tz="UTC")
        order = Order(
            order_id="12345",
            client_order_id="client-001",
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            limit_price=Decimal("150.00"),
            stop_price=None,
            status=OrderStatus.SUBMITTED,
            submitted_at=timestamp,
        )
        
        assert order.order_id == "12345"
        assert order.client_order_id == "client-001"
        assert order.status == OrderStatus.SUBMITTED
        assert order.submitted_at.tz is not None  # Ensure timezone aware
        assert order.filled_quantity == Decimal("0")
        assert order.average_fill_price is None

    def test_order_with_partial_fill(self) -> None:
        """Test order with partial fill."""
        timestamp = pd.Timestamp.now(tz="UTC")
        order = Order(
            order_id="12345",
            client_order_id=None,
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            limit_price=None,
            stop_price=None,
            status=OrderStatus.PARTIALLY_FILLED,
            submitted_at=timestamp,
            filled_quantity=Decimal("50"),
            average_fill_price=Decimal("151.25"),
        )
        
        assert order.filled_quantity == Decimal("50")
        assert order.average_fill_price == Decimal("151.25")

    def test_order_timestamp_is_utc(self) -> None:
        """Test that order timestamp is UTC aware."""
        timestamp = pd.Timestamp.now(tz="UTC")
        order = Order(
            order_id="12345",
            client_order_id=None,
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            limit_price=None,
            stop_price=None,
            status=OrderStatus.SUBMITTED,
            submitted_at=timestamp,
        )
        
        assert order.submitted_at.tz is not None
        assert str(order.submitted_at.tz) == "UTC"


@pytest.mark.unit
class TestFill:
    """Test Fill data model."""

    def test_create_fill(self) -> None:
        """Test creating a fill."""
        timestamp = pd.Timestamp.now(tz="UTC")
        fill = Fill(
            fill_id="fill-001",
            order_id="12345",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("151.50"),
            side=Side.BUY,
            timestamp=timestamp,
            commission=Decimal("1.00"),
        )
        
        assert fill.fill_id == "fill-001"
        assert fill.order_id == "12345"
        assert fill.quantity == Decimal("100")
        assert fill.price == Decimal("151.50")
        assert fill.commission == Decimal("1.00")
        assert fill.timestamp.tz is not None

    def test_fill_without_commission(self) -> None:
        """Test fill without commission data."""
        timestamp = pd.Timestamp.now(tz="UTC")
        fill = Fill(
            fill_id="fill-002",
            order_id="12345",
            symbol="AAPL",
            quantity=Decimal("50"),
            price=Decimal("151.75"),
            side=Side.BUY,
            timestamp=timestamp,
        )
        
        assert fill.commission is None


@pytest.mark.unit
class TestPosition:
    """Test Position data model."""

    def test_create_long_position(self) -> None:
        """Test creating a long position."""
        timestamp = pd.Timestamp.now(tz="UTC")
        position = Position(
            symbol="AAPL",
            quantity=Decimal("100"),
            average_cost=Decimal("150.00"),
            market_value=Decimal("15100.00"),
            unrealized_pnl=Decimal("100.00"),
            timestamp=timestamp,
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")  # Positive = long
        assert position.average_cost == Decimal("150.00")
        assert position.unrealized_pnl == Decimal("100.00")

    def test_create_short_position(self) -> None:
        """Test creating a short position."""
        timestamp = pd.Timestamp.now(tz="UTC")
        position = Position(
            symbol="TSLA",
            quantity=Decimal("-50"),  # Negative = short
            average_cost=Decimal("250.00"),
            market_value=Decimal("-12400.00"),
            unrealized_pnl=Decimal("100.00"),
            timestamp=timestamp,
        )
        
        assert position.quantity == Decimal("-50")  # Short position
        assert position.quantity < 0

