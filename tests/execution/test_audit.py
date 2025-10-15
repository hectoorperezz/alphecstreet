"""Tests for audit logging."""

from decimal import Decimal
import logging
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from execution.audit import AuditLogger
from execution.models import (
    OrderRequest,
    Order,
    Fill,
    OrderType,
    Side,
    OrderStatus,
)


@pytest.mark.unit
class TestAuditLogger:
    """Test audit logger functionality."""

    @pytest.fixture
    def audit_logger(self) -> AuditLogger:
        """Create an audit logger instance."""
        return AuditLogger()

    def test_log_order_submitted(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging order submission."""
        caplog.set_level(logging.INFO)
        
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            client_order_id="test-001",
        )
        
        order = Order(
            order_id="12345",
            client_order_id="test-001",
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            limit_price=None,
            stop_price=None,
            status=OrderStatus.SUBMITTED,
            submitted_at=pd.Timestamp.now(tz="UTC"),
        )
        
        audit_logger.log_order_submitted(request, order)
        
        # Verify log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "INFO"
        assert "ORDER_SUBMITTED" in record.message
        assert "AAPL" in record.message
        assert "test-001" in record.message

    def test_log_order_status_change(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging order status changes."""
        caplog.set_level(logging.INFO)
        
        order = Order(
            order_id="12345",
            client_order_id="test-001",
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
        
        audit_logger.log_order_status_change(order, OrderStatus.SUBMITTED)
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "ORDER_STATUS_CHANGE" in record.message
        assert "SUBMITTED" in record.message
        assert "FILLED" in record.message

    def test_log_fill(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging order fills."""
        caplog.set_level(logging.INFO)
        
        fill = Fill(
            fill_id="fill-001",
            order_id="12345",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("151.50"),
            side=Side.BUY,
            timestamp=pd.Timestamp.now(tz="UTC"),
            commission=Decimal("1.00"),
        )
        
        audit_logger.log_fill(fill)
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "ORDER_FILL" in record.message
        assert "AAPL" in record.message
        assert "151.50" in record.message

    def test_log_order_cancelled(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging order cancellations."""
        caplog.set_level(logging.INFO)
        
        audit_logger.log_order_cancelled("12345", "User requested cancellation")
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "ORDER_CANCELLED" in record.message
        assert "12345" in record.message
        assert "User requested cancellation" in record.message

    def test_log_order_rejected(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging order rejections."""
        caplog.set_level(logging.WARNING)
        
        order = Order(
            order_id="12345",
            client_order_id="test-001",
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            limit_price=None,
            stop_price=None,
            status=OrderStatus.REJECTED,
            submitted_at=pd.Timestamp.now(tz="UTC"),
        )
        
        audit_logger.log_order_rejected(order, "Insufficient margin")
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "ORDER_REJECTED" in record.message
        assert "Insufficient margin" in record.message

    def test_log_connection_event(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging connection events."""
        caplog.set_level(logging.INFO)
        
        audit_logger.log_connection_event("CONNECTED", {"host": "127.0.0.1", "port": 7497})
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "CONNECTION_EVENT" in record.message
        assert "CONNECTED" in record.message
        assert "127.0.0.1" in record.message

    def test_log_risk_check_failure(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging risk check failures."""
        caplog.set_level(logging.WARNING)
        
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("10000"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        audit_logger.log_risk_check_failure(request, "Position limit exceeded")
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "RISK_CHECK_FAILED" in record.message
        assert "Position limit exceeded" in record.message

    def test_structured_logging_format(self, audit_logger: AuditLogger, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logs are structured with key information."""
        caplog.set_level(logging.INFO)
        
        request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            client_order_id="test-001",
        )
        
        order = Order(
            order_id="12345",
            client_order_id="test-001",
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            limit_price=None,
            stop_price=None,
            status=OrderStatus.SUBMITTED,
            submitted_at=pd.Timestamp.now(tz="UTC"),
        )
        
        audit_logger.log_order_submitted(request, order)
        
        # Check that log contains correlation between client_order_id and order_id
        record = caplog.records[0]
        assert "test-001" in record.message
        assert "12345" in record.message

