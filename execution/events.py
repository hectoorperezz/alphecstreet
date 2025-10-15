"""Event handler protocols for execution events."""

from typing import Protocol

from execution.models import Order, Fill


class OrderEventHandler(Protocol):
    """Protocol for handling order events."""

    def on_order_status(self, order: Order) -> None:
        """
        Called when order status changes.

        Args:
            order: The order with updated status
        """
        ...

    def on_fill(self, fill: Fill) -> None:
        """
        Called when order is filled (partial or complete).

        Args:
            fill: The fill event
        """
        ...

    def on_order_rejected(self, order: Order, reason: str) -> None:
        """
        Called when order is rejected.

        Args:
            order: The rejected order
            reason: Rejection reason from broker
        """
        ...


class ConnectionEventHandler(Protocol):
    """Protocol for handling connection events."""

    def on_connected(self) -> None:
        """Called when connection established."""
        ...

    def on_disconnected(self) -> None:
        """Called when connection lost."""
        ...

