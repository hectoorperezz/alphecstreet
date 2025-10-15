# IBKR Execution Library Examples

This directory contains example scripts demonstrating how to use the IBKR order execution library.

## Prerequisites

1. **IBKR Account**: You need an Interactive Brokers account (paper trading recommended for testing)
2. **TWS Running**: Have Trader Workstation or IB Gateway running and API enabled
3. **Python Environment**: Ensure you've installed the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Before running the examples, ensure TWS is configured:

1. **Enable API Access**:
   - TWS: File → Global Configuration → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Add `127.0.0.1` to "Trusted IP Addresses"
   - Set Socket Port: `7497` (paper) or `7496` (live)

2. **Read-Only Mode** (for initial testing):
   - Check "Read-Only API" for safe testing
   - Uncheck when ready to submit real orders

## Examples

### 1. Interactive Order Tester (`interactive_order_tester.py`) 🆕

**Programa interactivo en español** para crear y ejecutar órdenes personalizadas:
- Menú interactivo fácil de usar
- Crear órdenes de mercado, límite, stop y stop-límite
- Ver órdenes abiertas en tiempo real
- Cancelar órdenes
- Ver posiciones actuales
- Historial de órdenes de la sesión

**Ejecutar:**
```bash
python examples/interactive_order_tester.py
```

**Funciones:**
1. 📈 Crear órdenes de mercado (Market)
2. 📊 Crear órdenes límite (Limit)
3. 🛑 Crear órdenes stop
4. 🔄 Crear órdenes stop-límite
5. 📋 Ver órdenes abiertas
6. ❌ Cancelar órdenes
7. 💼 Ver posiciones actuales
8. 📝 Ver historial de la sesión

### 2. Basic Order Submission (`basic_order_submission.py`)

Demonstrates the fundamental order lifecycle:
- Connecting to TWS
- Submitting market orders
- Submitting limit orders
- Checking order status
- Retrieving open orders
- Cancelling orders
- Querying positions
- Graceful disconnection

**Run it:**
```bash
python examples/basic_order_submission.py
```

**What it does:**
1. Connects to paper trading account (port 7497)
2. Submits a market buy order for 1 share of AAPL
3. Submits a limit buy order for 1 share of AAPL at $1 (won't fill)
4. Checks the limit order status
5. Lists all open orders
6. Cancels the limit order
7. Shows current positions
8. Disconnects

### 3. Risk Checks (`with_risk_checks.py`)

Shows how to implement and use risk check callbacks:
- Defining position limits
- Validating order size
- Validating order value
- Handling risk check rejections

**Run it:**
```bash
python examples/with_risk_checks.py
```

**What it does:**
1. Defines risk limits (max quantity: 100 shares, max value: $10,000)
2. Submits a small order that passes checks (10 shares)
3. Attempts to submit an order exceeding quantity limit (200 shares) - gets rejected
4. Attempts to submit an order exceeding value limit ($20,000) - gets rejected
5. Verifies that rejected orders are properly blocked before reaching TWS

## Common Patterns

### Connecting to TWS

```python
from execution import IBKRConnectionManager

manager = IBKRConnectionManager(
    host="127.0.0.1",
    port=7497,  # 7497=paper, 7496=live
    client_id=1,
    readonly=False,
)

await manager.connect()
# ... use connection ...
await manager.disconnect()
```

### Submitting Orders

```python
from decimal import Decimal
from execution import IBKROrderExecutor, OrderRequest, OrderType, Side

executor = IBKROrderExecutor(connection_manager=manager)

# Market order
request = OrderRequest(
    symbol="AAPL",
    quantity=Decimal("100"),
    order_type=OrderType.MARKET,
    side=Side.BUY,
)
order = await executor.submit_order(request)

# Limit order
request = OrderRequest(
    symbol="TSLA",
    quantity=Decimal("50"),
    order_type=OrderType.LIMIT,
    side=Side.SELL,
    limit_price=Decimal("250.50"),
)
order = await executor.submit_order(request)
```

### Risk Checks

```python
def my_risk_check(request: OrderRequest) -> bool:
    # Return True to approve, False to reject
    if request.quantity > Decimal("1000"):
        return False  # Reject large orders
    return True

executor = IBKROrderExecutor(
    connection_manager=manager,
    risk_check_callback=my_risk_check,
)
```

### Error Handling

```python
from execution import RiskCheckError, OrderRejectedError, ConnectionError

try:
    order = await executor.submit_order(request)
except RiskCheckError:
    print("Order blocked by risk checks")
except OrderRejectedError as e:
    print(f"Order rejected by broker: {e}")
except ConnectionError:
    print("Not connected to TWS")
```

## Best Practices

1. **Always Test on Paper First**: Use paper trading (port 7497) before going live
2. **Use Decimal for Money**: Always use `Decimal` for quantities and prices to avoid floating point errors
3. **Handle Exceptions**: Wrap order submissions in try/except blocks
4. **Implement Risk Checks**: Always validate orders before submission
5. **Check Connection**: Use `ensure_connected()` before operations
6. **Graceful Shutdown**: Always disconnect in a `finally` block
7. **Monitor Logs**: Enable logging to track execution flow
8. **Use Client Order IDs**: Include `client_order_id` for correlation tracking

## Troubleshooting

### Connection Refused
- Ensure TWS/Gateway is running
- Check that API is enabled in TWS settings
- Verify port number (7497 for paper, 7496 for live)
- Confirm `127.0.0.1` is in Trusted IP Addresses

### "Read-Only API" Error
- Uncheck "Read-Only API" in TWS settings
- Restart TWS after changing this setting

### Orders Not Filling
- Check that you have sufficient funds/margin
- For limit orders, ensure price is near market
- Review order status for rejection reasons

### "Client ID Already in Use"
- Each connection needs a unique client ID
- Disconnect existing connections or use different ID
- Restart TWS if issue persists

## Next Steps

1. Review the [Design Document](../execution/DESIGN.md) for architecture details
2. Read the [Setup Guide](../SETUP.md) for environment configuration
3. Check the [Requirements](../execution/README.md) for module overview
4. Explore the [Test Suite](../tests/execution/) for more usage patterns

## Support

For issues or questions:
- Review the [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- Check the [ib_insync Documentation](https://ib-insync.readthedocs.io/)
- Examine the test suite for edge cases and patterns

