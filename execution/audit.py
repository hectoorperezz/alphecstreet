"""Audit logging for execution events."""

import json
import logging
from typing import Any, Dict

from execution.models import Order, OrderRequest, Fill, OrderStatus


logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Logs all execution events for compliance and debugging.

    All logs are structured with key information for easy parsing and analysis.
    Logs include correlation IDs to track orders from request through fills.
    """

    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize audit logger.

        Args:
            log_level: Logging level (default: INFO)
        """
        self.logger = logging.getLogger("execution.audit")
        self.logger.setLevel(log_level)

    def log_order_submitted(self, request: OrderRequest, order: Order) -> None:
        """
        Log order submission with correlation ID.

        Args:
            request: The original order request
            order: The submitted order with broker ID
        """
        log_data = {
            "event": "ORDER_SUBMITTED",
            "order_id": order.order_id,
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "quantity": str(request.quantity),
            "order_type": request.order_type.value,
            "side": request.side.value,
            "limit_price": str(request.limit_price) if request.limit_price else None,
            "stop_price": str(request.stop_price) if request.stop_price else None,
            "time_in_force": request.time_in_force.value,
            "submitted_at": order.submitted_at.isoformat(),
        }
        self.logger.info(self._format_log_message(log_data))

    def log_order_status_change(self, order: Order, old_status: OrderStatus) -> None:
        """
        Log status transitions.

        Args:
            order: The order with new status
            old_status: Previous order status
        """
        log_data = {
            "event": "ORDER_STATUS_CHANGE",
            "order_id": order.order_id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "old_status": old_status.value,
            "new_status": order.status.value,
            "filled_quantity": str(order.filled_quantity),
            "average_fill_price": (
                str(order.average_fill_price) if order.average_fill_price else None
            ),
        }
        self.logger.info(self._format_log_message(log_data))

    def log_fill(self, fill: Fill) -> None:
        """
        Log execution fills.

        Args:
            fill: The fill event
        """
        log_data = {
            "event": "ORDER_FILL",
            "fill_id": fill.fill_id,
            "order_id": fill.order_id,
            "symbol": fill.symbol,
            "quantity": str(fill.quantity),
            "price": str(fill.price),
            "side": fill.side.value,
            "commission": str(fill.commission) if fill.commission else None,
            "timestamp": fill.timestamp.isoformat(),
        }
        self.logger.info(self._format_log_message(log_data))

    def log_order_cancelled(self, order_id: str, reason: str) -> None:
        """
        Log cancellations.

        Args:
            order_id: The cancelled order ID
            reason: Reason for cancellation
        """
        log_data = {
            "event": "ORDER_CANCELLED",
            "order_id": order_id,
            "reason": reason,
        }
        self.logger.info(self._format_log_message(log_data))

    def log_order_rejected(self, order: Order, reason: str) -> None:
        """
        Log order rejections.

        Args:
            order: The rejected order
            reason: Rejection reason from broker
        """
        log_data = {
            "event": "ORDER_REJECTED",
            "order_id": order.order_id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "quantity": str(order.quantity),
            "order_type": order.order_type.value,
            "side": order.side.value,
            "reason": reason,
        }
        self.logger.warning(self._format_log_message(log_data))

    def log_connection_event(self, event: str, details: Dict[str, Any]) -> None:
        """
        Log connection state changes.

        Args:
            event: Event type (e.g., "CONNECTED", "DISCONNECTED")
            details: Additional event details
        """
        log_data = {
            "event": "CONNECTION_EVENT",
            "connection_event": event,
            **details,
        }
        self.logger.info(self._format_log_message(log_data))

    def log_risk_check_failure(self, request: OrderRequest, reason: str) -> None:
        """
        Log risk check failures.

        Args:
            request: The order request that failed risk checks
            reason: Reason for rejection
        """
        log_data = {
            "event": "RISK_CHECK_FAILED",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "quantity": str(request.quantity),
            "order_type": request.order_type.value,
            "side": request.side.value,
            "reason": reason,
        }
        self.logger.warning(self._format_log_message(log_data))

    def _format_log_message(self, log_data: Dict[str, Any]) -> str:
        """
        Format log data as structured JSON string.

        Args:
            log_data: Dictionary of log data

        Returns:
            JSON formatted log message
        """
        return json.dumps(log_data, default=str)

