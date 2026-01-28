"""Tests for TWS client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ibkr_tws_mcp.tws_client import TWSClientWrapper


class TestTWSClientInitialization:
    """Tests for TWS client initialization."""

    def test_default_initialization(self) -> None:
        """Test client initialization with default values."""
        client = TWSClientWrapper()

        assert client.host == "127.0.0.1"
        assert client.port == 7496
        assert client.client_id == 0
        assert client.timeout == 30
        assert client._connected is False

    def test_custom_initialization(self) -> None:
        """Test client initialization with custom values."""
        client = TWSClientWrapper(
            host="192.168.1.100",
            port=7497,
            client_id=5,
            timeout=60,
        )

        assert client.host == "192.168.1.100"
        assert client.port == 7497
        assert client.client_id == 5
        assert client.timeout == 60


class TestTWSClientConnection:
    """Tests for TWS client connection management."""

    def test_is_connected_false_initially(self) -> None:
        """Test that client is not connected initially."""
        client = TWSClientWrapper()

        assert client.is_connected() is False

    def test_disconnect_when_not_connected(self) -> None:
        """Test disconnecting when not connected."""
        client = TWSClientWrapper()
        client.disconnect_client()

        assert client._connected is False


class TestTWSClientRequestId:
    """Tests for request ID generation."""

    def test_request_id_increments(self) -> None:
        """Test that request IDs increment."""
        client = TWSClientWrapper()

        id1 = client._get_next_req_id()
        id2 = client._get_next_req_id()
        id3 = client._get_next_req_id()

        assert id2 == id1 + 1
        assert id3 == id2 + 1


class TestTWSClientQueues:
    """Tests for queue management."""

    def test_create_response_queue(self) -> None:
        """Test creating a response queue."""
        client = TWSClientWrapper()
        req_id = 1

        queue = client._create_response_queue(req_id)

        assert req_id in client._response_queues
        assert queue is client._response_queues[req_id]

    def test_cleanup_response_queue(self) -> None:
        """Test cleaning up a response queue."""
        client = TWSClientWrapper()
        req_id = 1

        client._create_response_queue(req_id)
        client._cleanup_response_queue(req_id)

        assert req_id not in client._response_queues


class TestTWSClientManagedAccounts:
    """Tests for managed accounts."""

    def test_get_managed_accounts_empty(self) -> None:
        """Test getting managed accounts when empty."""
        client = TWSClientWrapper()

        assert client.get_managed_accounts() == []

    def test_managed_accounts_callback(self) -> None:
        """Test managed accounts callback."""
        client = TWSClientWrapper()
        client.managedAccounts("DU123456,DU789012")

        accounts = client.get_managed_accounts()

        assert "DU123456" in accounts
        assert "DU789012" in accounts


class TestTWSClientNextValidId:
    """Tests for next valid order ID."""

    def test_next_valid_id_callback(self) -> None:
        """Test next valid ID callback."""
        client = TWSClientWrapper()
        client.nextValidId(100)

        assert client._next_valid_id == 100
        assert client._connection_event.is_set()

    def test_get_next_order_id_not_connected(self) -> None:
        """Test getting next order ID when not connected."""
        client = TWSClientWrapper()

        with pytest.raises(RuntimeError, match="Not connected"):
            client.get_next_order_id()

    def test_get_next_order_id_increments(self) -> None:
        """Test that getting next order ID increments the counter."""
        client = TWSClientWrapper()
        client._next_valid_id = 100

        id1 = client.get_next_order_id()
        id2 = client.get_next_order_id()

        assert id1 == 100
        assert id2 == 101


class TestTWSClientErrorHandling:
    """Tests for error handling."""

    def test_error_callback_info_message(self) -> None:
        """Test error callback with info message."""
        client = TWSClientWrapper()
        client.error(-1, 2104, "Market data farm connection is OK")

        assert client._last_error == (-1, 2104, "Market data farm connection is OK")

    def test_error_callback_system_error(self) -> None:
        """Test error callback with system error."""
        client = TWSClientWrapper()
        client.error(-1, 502, "Couldn't connect to TWS")

        assert client._last_error == (-1, 502, "Couldn't connect to TWS")

    def test_error_callback_adds_to_request_queue(self) -> None:
        """Test that errors are added to request queues."""
        client = TWSClientWrapper()
        req_id = 1
        client._create_response_queue(req_id)

        client.error(req_id, 200, "No security definition found")

        assert not client._response_queues[req_id].empty()
        item = client._response_queues[req_id].get_nowait()
        assert item[0] == "ERROR"
        assert item[1] == 200
