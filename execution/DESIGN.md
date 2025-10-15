# IBKR Order Execution Library - Architecture Design

## Overview

This document defines the architecture for the foundational IBKR Trader Workstation order execution library. The design prioritizes reliability, testability, and clean abstractions while keeping initial scope focused on core functionality.

## Design Principles

1. **Separation of Concerns**: Isolate TWS API specifics from business logic
2. **Testability**: Use dependency injection to enable unit testing without live connections
3. **Type Safety**: Comprehensive type hints throughout
4. **Auditability**: Log all state transitions and API interactions
5. **Extensibility**: Design interfaces that can support future enhancements
6. **Financial Precision**: Use `Decimal` for all monetary values, UTC timestamps for all times

## Core Components

### 1. Data Models (`execution/models.py`)

Immutable dataclasses representing domain concepts:

```python
@dataclass(frozen=True)
class OrderRequest:
    """Request to submit an order."""
    symbol: str
    quantity: Decimal
    order_type: OrderType  # MARKET, LIMIT, STOP, STOP_LIMIT
    side: Side  # BUY, SELL
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    account: Optional[str] = None
    client_order_id: Optional[str] = None  # For correlation

@dataclass(frozen=True)
class Order:
    """Submitted order with broker assignment."""
    order_id: str  # Broker-assigned ID
    client_order_id: Optional[str]
    symbol: str
    quantity: Decimal
    order_type: OrderType
    side: Side
    limit_price: Optional[Decimal]
    stop_price: Optional[Decimal]
    status: OrderStatus  # PENDING, SUBMITTED, FILLED, CANCELLED, REJECTED
    submitted_at: pd.Timestamp  # UTC
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Optional[Decimal] = None
    
@dataclass(frozen=True)
class Fill:
    """Execution fill event."""
    fill_id: str
    order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    side: Side
    timestamp: pd.Timestamp  # UTC
    commission: Optional[Decimal] = None
    
@dataclass(frozen=True)
class Position:
    """Current position snapshot."""
    symbol: str
    quantity: Decimal  # Positive=long, negative=short
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    timestamp: pd.Timestamp  # UTC
```

### 2. Connection Manager (`execution/connection.py`)

Handles TWS API connectivity lifecycle:

```python
class IBKRConnectionManager:
    """Manages connection to IBKR TWS/Gateway with automatic reconnection."""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,  # Paper trading default
        client_id: int = 1,
        readonly: bool = False,
    ):
        """Initialize connection parameters."""
        
    async def connect(self) -> None:
        """Establish connection to TWS."""
        
    async def disconnect(self) -> None:
        """Gracefully close connection."""
        
    def is_connected(self) -> bool:
        """Check connection status."""
        
    async def ensure_connected(self) -> None:
        """Reconnect if disconnected."""
        
    # Internal: handles reconnection logic with backoff
```

### 3. Order Executor (`execution/executor.py`)

Main interface for order operations:

```python
class IBKROrderExecutor:
    """High-level interface for order execution."""
    
    def __init__(
        self,
        connection_manager: IBKRConnectionManager,
        risk_check_callback: Optional[Callable[[OrderRequest], bool]] = None,
    ):
        """Initialize with connection manager and optional risk checks."""
        
    async def submit_order(self, request: OrderRequest) -> Order:
        """
        Submit an order to IBKR.
        
        Raises:
            RiskCheckError: If risk check callback rejects order
            ConnectionError: If not connected to TWS
            OrderRejectedError: If IBKR rejects the order
        """
        
    async def cancel_order(self, order_id: str) -> None:
        """Cancel an open order."""
        
    async def get_order_status(self, order_id: str) -> Order:
        """Query current order status."""
        
    async def get_open_orders(self) -> List[Order]:
        """Retrieve all open orders."""
        
    async def get_positions(self) -> List[Position]:
        """Retrieve current positions."""
        
    # Internal: converts between domain models and ib_insync objects
```

### 4. Event Handlers (`execution/events.py`)

Callback interfaces for asynchronous events:

```python
class OrderEventHandler(Protocol):
    """Protocol for handling order events."""
    
    def on_order_status(self, order: Order) -> None:
        """Called when order status changes."""
        
    def on_fill(self, fill: Fill) -> None:
        """Called when order is filled (partial or complete)."""
        
    def on_order_rejected(self, order: Order, reason: str) -> None:
        """Called when order is rejected."""

class ConnectionEventHandler(Protocol):
    """Protocol for handling connection events."""
    
    def on_connected(self) -> None:
        """Called when connection established."""
        
    def on_disconnected(self) -> None:
        """Called when connection lost."""
```

### 5. Audit Logger (`execution/audit.py`)

Structured logging for compliance:

```python
class AuditLogger:
    """Logs all execution events for compliance and debugging."""
    
    def log_order_submitted(self, request: OrderRequest, order: Order) -> None:
        """Log order submission with correlation ID."""
        
    def log_order_status_change(self, order: Order, old_status: OrderStatus) -> None:
        """Log status transitions."""
        
    def log_fill(self, fill: Fill) -> None:
        """Log execution fills."""
        
    def log_order_cancelled(self, order_id: str, reason: str) -> None:
        """Log cancellations."""
        
    def log_connection_event(self, event: str, details: Dict[str, Any]) -> None:
        """Log connection state changes."""
```

## Interaction Flows

### Submit Order Flow

```
Strategy/Client
    |
    v
OrderRequest --> risk_check_callback (if configured)
    |                   |
    |                   v (rejected)
    |              RiskCheckError
    |
    v (approved)
IBKROrderExecutor.submit_order()
    |
    v
ConnectionManager.ensure_connected()
    |
    v
Convert OrderRequest -> ib_insync.Order
    |
    v
ib_insync.IB.placeOrder()
    |
    v
AuditLogger.log_order_submitted()
    |
    v
Return Order (with broker order_id)
```

### Fill Event Flow

```
IBKR TWS
    |
    v
ib_insync execFillEvent
    |
    v
IBKROrderExecutor._handle_fill()
    |
    v
Convert ib_insync.Fill -> Fill
    |
    v
AuditLogger.log_fill()
    |
    v
OrderEventHandler.on_fill() (if registered)
```

## Error Handling Strategy

1. **Connection Errors**: Automatic retry with exponential backoff; emit connection events
2. **Order Rejections**: Raise `OrderRejectedError` with IBKR reason; log to audit trail
3. **Risk Check Failures**: Raise `RiskCheckError` before touching TWS; log rejection
4. **Invalid Parameters**: Raise `ValueError` immediately with clear message
5. **Timeout Errors**: Configurable timeout for order acknowledgement; raise `TimeoutError`

## Configuration

Environment variables or config file:

```
IBKR_HOST=127.0.0.1
IBKR_PORT=7497  # 7497=paper, 7496=live
IBKR_CLIENT_ID=1
IBKR_READONLY=false
IBKR_TIMEOUT_SECONDS=30
IBKR_RECONNECT_MAX_ATTEMPTS=5
IBKR_RECONNECT_BACKOFF_SECONDS=5
```

## Testing Strategy

1. **Unit Tests**: Mock `ib_insync.IB` to test logic without live connection
2. **Integration Tests**: Connect to IBKR demo environment; verify round-trip order lifecycle
3. **Resilience Tests**: Simulate disconnections, rejections, timeouts
4. **Data Validation Tests**: Ensure Decimal precision maintained, timestamps always UTC

## Dependencies

- `ib_insync>=0.9.86`: IBKR TWS API wrapper
- `pandas>=2.0`: Timestamp handling
- `python>=3.11`: Modern type hints
- `pytest>=7.0`: Testing framework
- `pytest-asyncio`: Async test support
- `pytest-mock`: Mocking utilities

## Future Enhancements (Out of Scope for V1)

- Bracket orders (parent + profit target + stop loss)
- Order modifications (price/quantity adjustments)
- Advanced order types (trailing stop, market-on-close, etc.)
- Multi-account support
- Real-time P&L tracking
- Position reconciliation against risk limits
- Performance metrics (latency tracking, fill quality analysis)

