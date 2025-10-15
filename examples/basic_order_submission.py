"""
Basic example of submitting orders using the IBKR execution library.

This example demonstrates:
- Connecting to IBKR TWS
- Submitting market and limit orders
- Checking order status
- Cancelling orders
- Graceful disconnection
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
    TimeInForce,
) 

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main execution flow."""
    
    # Step 1: Create connection manager
    logger.info("Creating connection manager...")
    manager = IBKRConnectionManager(
        host="127.0.0.1",
        port=7497,  # Paper trading port
        client_id=1,
        readonly=False,
    )

    try:
        # Step 2: Connect to TWS
        logger.info("Connecting to IBKR TWS...")
        await manager.connect()
        logger.info("Connected successfully!")

        # Step 3: Create executor
        executor = IBKROrderExecutor(connection_manager=manager)

        # Step 4: Submit a market order
        logger.info("Submitting market order...")
        market_order_request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
            side=Side.BUY,
            client_order_id="example-market-001",
        )
        
        market_order = await executor.submit_order(market_order_request)
        logger.info(
            f"Market order submitted: ID={market_order.order_id}, "
            f"Status={market_order.status.value}"
        )

        # Step 5: Submit a limit order (far from market to avoid fill)
        logger.info("Submitting limit order...")
        limit_order_request = OrderRequest(
            symbol="AAPL",
            quantity=Decimal("1"),
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            limit_price=Decimal("1.00"),  # Far below market price
            time_in_force=TimeInForce.GTC,
            client_order_id="example-limit-001",
        )
        
        limit_order = await executor.submit_order(limit_order_request)
        logger.info(
            f"Limit order submitted: ID={limit_order.order_id}, "
            f"Status={limit_order.status.value}, "
            f"Limit Price=${limit_order.limit_price}"
        )

        # Step 6: Wait a moment then check order status
        await asyncio.sleep(2)
        
        logger.info("Checking order status...")
        updated_limit_order = await executor.get_order_status(limit_order.order_id)
        logger.info(
            f"Limit order status: {updated_limit_order.status.value}, "
            f"Filled: {updated_limit_order.filled_quantity}"
        )

        # Step 7: Get all open orders
        logger.info("Retrieving open orders...")
        open_orders = await executor.get_open_orders()
        logger.info(f"Found {len(open_orders)} open order(s)")
        for order in open_orders:
            logger.info(
                f"  - Order {order.order_id}: {order.side.value} {order.quantity} "
                f"{order.symbol} @ {order.order_type.value}"
            )

        # Step 8: Cancel the limit order
        logger.info(f"Cancelling limit order {limit_order.order_id}...")
        await executor.cancel_order(limit_order.order_id)
        logger.info("Order cancelled successfully")

        # Step 9: Get current positions
        logger.info("Retrieving positions...")
        positions = await executor.get_positions()
        if positions:
            logger.info(f"Found {len(positions)} position(s):")
            for pos in positions:
                logger.info(
                    f"  - {pos.symbol}: {pos.quantity} shares, "
                    f"Avg Cost: ${pos.average_cost}, "
                    f"Market Value: ${pos.market_value}"
                )
        else:
            logger.info("No open positions")

    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
    finally:
        # Step 10: Disconnect
        logger.info("Disconnecting from TWS...")
        await manager.disconnect()
        logger.info("Disconnected successfully")


if __name__ == "__main__":
    asyncio.run(main())































