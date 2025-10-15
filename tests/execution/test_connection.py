"""Tests for IBKR connection manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from execution.connection import IBKRConnectionManager, ConnectionError


@pytest.mark.unit
class TestConnectionManager:
    """Test connection manager functionality."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        manager = IBKRConnectionManager()
        
        assert manager.host == "127.0.0.1"
        assert manager.port == 7497  # Paper trading default
        assert manager.client_id == 1
        assert manager.readonly is False

    def test_init_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        manager = IBKRConnectionManager(
            host="192.168.1.100",
            port=7496,  # Live trading
            client_id=5,
            readonly=True,
        )
        
        assert manager.host == "192.168.1.100"
        assert manager.port == 7496
        assert manager.client_id == 5
        assert manager.readonly is True

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful connection to TWS."""
        manager = IBKRConnectionManager()
        
        with patch("execution.connection.IB") as mock_ib:
            mock_ib_instance = AsyncMock()
            mock_ib.return_value = mock_ib_instance
            mock_ib_instance.connectAsync.return_value = None
            mock_ib_instance.isConnected.return_value = True
            
            await manager.connect()
            
            assert manager.is_connected()
            mock_ib_instance.connectAsync.assert_called_once_with(
                "127.0.0.1", 7497, clientId=1, readonly=False
            )

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """Test connection failure handling."""
        manager = IBKRConnectionManager()
        
        with patch("execution.connection.IB") as mock_ib:
            mock_ib_instance = AsyncMock()
            mock_ib.return_value = mock_ib_instance
            mock_ib_instance.connectAsync.side_effect = ConnectionError("Connection refused")
            
            with pytest.raises(ConnectionError):
                await manager.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test graceful disconnection."""
        manager = IBKRConnectionManager()
        
        with patch("execution.connection.IB") as mock_ib:
            mock_ib_instance = AsyncMock()
            mock_ib.return_value = mock_ib_instance
            mock_ib_instance.connectAsync.return_value = None
            mock_ib_instance.isConnected.return_value = True
            
            await manager.connect()
            await manager.disconnect()
            
            mock_ib_instance.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_connected_when_disconnected(self) -> None:
        """Test is_connected returns False when not connected."""
        manager = IBKRConnectionManager()
        
        assert not manager.is_connected()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_connected(self) -> None:
        """Test ensure_connected does nothing when already connected."""
        manager = IBKRConnectionManager()
        
        with patch("execution.connection.IB") as mock_ib:
            mock_ib_instance = AsyncMock()
            mock_ib.return_value = mock_ib_instance
            mock_ib_instance.connectAsync.return_value = None
            mock_ib_instance.isConnected.return_value = True
            
            await manager.connect()
            
            # Reset mock to check it's not called again
            mock_ib_instance.connectAsync.reset_mock()
            
            await manager.ensure_connected()
            
            # Should not try to connect again
            mock_ib_instance.connectAsync.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_disconnected(self) -> None:
        """Test ensure_connected reconnects when disconnected."""
        manager = IBKRConnectionManager()
        
        with patch("execution.connection.IB") as mock_ib:
            mock_ib_instance = AsyncMock()
            mock_ib.return_value = mock_ib_instance
            mock_ib_instance.connectAsync.return_value = None
            mock_ib_instance.isConnected.return_value = False
            
            await manager.ensure_connected()
            
            mock_ib_instance.connectAsync.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_with_backoff(self) -> None:
        """Test reconnection with exponential backoff."""
        manager = IBKRConnectionManager(max_reconnect_attempts=3)
        
        with patch("execution.connection.IB") as mock_ib:
            mock_ib_instance = AsyncMock()
            mock_ib.return_value = mock_ib_instance
            
            # Fail twice, succeed on third attempt
            mock_ib_instance.connectAsync.side_effect = [
                ConnectionError("Failed"),
                ConnectionError("Failed"),
                None,  # Success
            ]
            mock_ib_instance.isConnected.return_value = True
            
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await manager.connect_with_retry()
                
                # Should have called sleep twice (after first two failures)
                assert mock_sleep.call_count == 2


@pytest.mark.integration
class TestConnectionManagerIntegration:
    """Integration tests requiring TWS connection."""

    @pytest.mark.asyncio
    async def test_connect_to_real_tws(self) -> None:
        """Test connecting to actual TWS instance."""
        # This test requires TWS to be running
        manager = IBKRConnectionManager(port=7497)  # Paper trading
        
        try:
            await manager.connect()
            assert manager.is_connected()
        except ConnectionError:
            pytest.skip("TWS not available")
        finally:
            await manager.disconnect()

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self) -> None:
        """Test reconnection after disconnection."""
        manager = IBKRConnectionManager(port=7497)
        
        try:
            await manager.connect()
            assert manager.is_connected()
            
            await manager.disconnect()
            assert not manager.is_connected()
            
            await manager.connect()
            assert manager.is_connected()
        except ConnectionError:
            pytest.skip("TWS not available")
        finally:
            await manager.disconnect()

