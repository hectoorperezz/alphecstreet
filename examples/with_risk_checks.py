"""
Example of using the execution library with risk checks.

This example demonstrates:
- Implementing a custom risk check callback
- Blocking orders that exceed position limits
- Handling risk check failures
"""

import asyncio
import logging
from decimal import Decimal

from execution import (
    IBKRConnectionManager,
    IBKROrderExecutor,
    OrderRequest,
    OrderType,
    Side,
    RiskCheckError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Define risk limits
MAX_ORDER_QUANTITY = Decimal("100")
MAX_ORDER_VALUE = Decimal("10000")  # $10,000


def risk_check_callback(request: OrderRequest) -> bool:
    """
    Custom risk check function.

    Args:
        request: The order request to validate

    Returns:
        True if order passes risk checks, False otherwise
    """
    logger.info(f"Running risk checks for {request.symbol}...")

    # Check 1: Order quantity limit
    if request.quantity > MAX_ORDER_QUANTITY:
        logger.warning(
            f"Risk check FAILED: Order quantity {request.quantity} "
            f"exceeds limit of {MAX_ORDER_QUANTITY}"
        )
        return False

    # Check 2: Order value limit (for limit orders)
    if request.limit_price is not None:
        order_value = request.quantity * request.limit_price
        if order_value > MAX_ORDER_VALUE:
            logger.warning(
                f"Risk check FAILED: Order value ${order_value} "
                f"exceeds limit of ${MAX_ORDER_VALUE}"
            )
            return False

    logger.info("Risk checks PASSED")
    return True


async def main() -> None:
    """Main execution flow."""
    
    # Create connection manager
    manager = IBKRConnectionManager(host="127.0.0.1", port=7497, client_id=1)

    try:
        # Connect to TWS
        await manager.connect()
        logger.info("Connected to TWS")

        # Create executor with risk check callback
        executor = IBKROrderExecutor(
            connection_manager=manager,
            risk_check_callback=risk_check_callback,
        )

        # Test 1: Submit order that passes risk checks
        logger.info("\n=== Test 1: Order that passes risk checks ===")
        small_order = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("10"),  # Within limit
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            limit_price=Decimal("150.00"),
        )
        
        try:
            order = await executor.submit_order(small_order)
            logger.info(f"✓ Order {order.order_id} submitted successfully")
            # Cancel it immediately
            await executor.cancel_order(order.order_id)
        except RiskCheckError as e:
            logger.error(f"✗ Risk check failed: {e}")

        # Test 2: Submit order that exceeds quantity limit
        logger.info("\n=== Test 2: Order exceeding quantity limit ===")
        large_quantity_order = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("200"),  # Exceeds MAX_ORDER_QUANTITY
            order_type=OrderType.MARKET,
            side=Side.BUY,
        )
        
        try:
            order = await executor.submit_order(large_quantity_order)
            logger.info(f"✓ Order {order.order_id} submitted (unexpected)")
        except RiskCheckError as e:
            logger.info(f"✓ Risk check correctly rejected order: {e}")

        # Test 3: Submit order that exceeds value limit
        logger.info("\n=== Test 3: Order exceeding value limit ===")
        large_value_order = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("100"),
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            limit_price=Decimal("200.00"),  # 100 * $200 = $20,000 > limit
        )
        
        try:
            order = await executor.submit_order(large_value_order)
            logger.info(f"✓ Order {order.order_id} submitted (unexpected)")
        except RiskCheckError as e:
            logger.info(f"✓ Risk check correctly rejected order: {e}")

        logger.info("\n=== All risk check tests completed ===")

    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
    finally:
        await manager.disconnect()
        logger.info("Disconnected from TWS")


if __name__ == "__main__":
    asyncio.run(main())

