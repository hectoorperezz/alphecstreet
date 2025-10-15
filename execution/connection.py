"""IBKR TWS connection management."""

import asyncio
import logging
from typing import Optional

from ib_insync import IB


logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Exception raised when connection to TWS fails."""

    pass


class IBKRConnectionManager:
    """
    Manages connection to IBKR TWS/Gateway with automatic reconnection.

    Attributes:
        host: TWS host address
        port: TWS port (7497 for paper, 7496 for live)
        client_id: Unique client identifier
        readonly: Whether to connect in read-only mode
        max_reconnect_attempts: Maximum reconnection attempts
        reconnect_backoff_seconds: Initial backoff time for reconnection

    Examples:
        >>> manager = IBKRConnectionManager(port=7497)  # Paper trading
        >>> await manager.connect()
        >>> assert manager.is_connected()
        >>> await manager.disconnect()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,  # Paper trading default
        client_id: int = 1,
        readonly: bool = False,
        max_reconnect_attempts: int = 5,
        reconnect_backoff_seconds: int = 5,
    ):
        """
        Initialize connection parameters.

        Args:
            host: TWS host address (default: 127.0.0.1)
            port: TWS port - 7497 for paper, 7496 for live (default: 7497)
            client_id: Unique client ID for this connection (default: 1)
            readonly: Connect in read-only mode (default: False)
            max_reconnect_attempts: Max reconnection attempts (default: 5)
            reconnect_backoff_seconds: Initial backoff for retry (default: 5)
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.readonly = readonly
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_backoff_seconds = reconnect_backoff_seconds

        self._ib: Optional[IB] = None
        self._connected = False

    async def connect(self) -> None:
        """
        Establish connection to TWS.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._ib = IB()
            await self._ib.connectAsync(
                self.host,
                self.port,
                clientId=self.client_id,
                readonly=self.readonly,
            )
            self._connected = True
            logger.info(
                f"Connected to IBKR TWS at {self.host}:{self.port} "
                f"(client_id={self.client_id}, readonly={self.readonly})"
            )
        except Exception as e:
            self._connected = False
            error_msg = f"Failed to connect to TWS at {self.host}:{self.port}: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

    async def disconnect(self) -> None:
        """Gracefully close connection."""
        if self._ib is not None and self._ib.isConnected():
            self._ib.disconnect()
            self._connected = False
            logger.info(f"Disconnected from IBKR TWS at {self.host}:{self.port}")

    def is_connected(self) -> bool:
        """
        Check connection status.

        Returns:
            True if connected to TWS, False otherwise
        """
        if self._ib is None:
            return False
        return self._ib.isConnected()

    async def ensure_connected(self) -> None:
        """
        Ensure connection is active, reconnect if necessary.

        Raises:
            ConnectionError: If reconnection fails
        """
        if not self.is_connected():
            logger.warning("Connection lost, attempting to reconnect...")
            await self.connect()

    async def connect_with_retry(self) -> None:
        """
        Connect with exponential backoff retry logic.

        Raises:
            ConnectionError: If all retry attempts fail
        """
        attempt = 0
        backoff = self.reconnect_backoff_seconds

        while attempt < self.max_reconnect_attempts:
            try:
                await self.connect()
                return  # Success
            except ConnectionError as e:
                attempt += 1
                if attempt >= self.max_reconnect_attempts:
                    error_msg = (
                        f"Failed to connect after {self.max_reconnect_attempts} attempts"
                    )
                    logger.error(error_msg)
                    raise ConnectionError(error_msg) from e

                logger.warning(
                    f"Connection attempt {attempt}/{self.max_reconnect_attempts} failed, "
                    f"retrying in {backoff} seconds..."
                )
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff

    def get_ib_client(self) -> IB:
        """
        Get the underlying ib_insync IB client.

        Returns:
            The IB client instance

        Raises:
            ConnectionError: If not connected
        """
        if self._ib is None or not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        return self._ib

