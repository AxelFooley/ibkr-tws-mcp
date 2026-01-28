"""Tests for IBKRTools class."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ibkr_tws_mcp.models import ContractSpec, OrderSpec, SecurityType
from ibkr_tws_mcp.tools import IBKRTools


class TestConnectionTools:
    """Tests for connection-related tools."""

    def test_connect_success(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test successful connection."""
        result = tools.connect()

        assert result["status"] == "connected"
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 7496
        mock_tws_client.connect_and_run.assert_called_once()

    def test_connect_failure(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test connection failure."""
        mock_tws_client.connect_and_run.side_effect = Exception("Connection refused")

        result = tools.connect()

        assert result["status"] == "error"
        assert "Connection refused" in result["error"]

    def test_disconnect(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test disconnection."""
        result = tools.disconnect()

        assert result["status"] == "disconnected"
        mock_tws_client.disconnect_client.assert_called_once()

    def test_connection_status(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test connection status check."""
        result = tools.connection_status()

        assert result["connected"] is True
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 7496

    def test_get_server_time(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting server time."""
        result = tools.get_server_time()

        assert result["server_time"] == 1704067200
        mock_tws_client.get_server_time.assert_called_once()


class TestAccountTools:
    """Tests for account-related tools."""

    def test_get_managed_accounts(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting managed accounts."""
        result = tools.get_managed_accounts()

        assert result == ["DU123456"]
        mock_tws_client.get_managed_accounts.assert_called_once()

    def test_get_account_summary(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting account summary."""
        result = tools.get_account_summary()

        assert result["account"] == "DU123456"
        assert len(result["items"]) == 3
        assert result["items"][0]["tag"] == "NetLiquidation"
        assert result["items"][0]["value"] == "100000.00"


class TestPositionTools:
    """Tests for position-related tools."""

    def test_get_positions(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting positions."""
        result = tools.get_positions()

        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["position"] == 100.0
        assert result[1]["symbol"] == "MSFT"
        assert result[1]["position"] == 50.0


class TestOrderTools:
    """Tests for order-related tools."""

    def test_get_open_orders(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting open orders."""
        result = tools.get_open_orders()

        assert result == []
        mock_tws_client.get_open_orders.assert_called_once()

    def test_place_order(
        self,
        tools: IBKRTools,
        mock_tws_client: MagicMock,
        sample_contract_spec: ContractSpec,
        sample_order_spec: OrderSpec,
    ) -> None:
        """Test placing an order."""
        result = tools.place_order(sample_contract_spec, sample_order_spec)

        assert result["order_id"] == 1
        assert result["status"] == "submitted"
        assert "order_state" in result
        mock_tws_client.place_order_sync.assert_called_once()

    def test_cancel_order(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test cancelling an order."""
        result = tools.cancel_order(1)

        assert result["order_id"] == 1
        assert result["status"] == "cancel_requested"
        mock_tws_client.cancel_order_sync.assert_called_once_with(1)

    def test_cancel_all_orders(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test cancelling all orders."""
        result = tools.cancel_all_orders()

        assert result["status"] == "cancel_all_requested"
        mock_tws_client.cancel_all_orders.assert_called_once()


class TestContractTools:
    """Tests for contract-related tools."""

    def test_get_contract_details(
        self, tools: IBKRTools, mock_tws_client: MagicMock, sample_contract_spec: ContractSpec
    ) -> None:
        """Test getting contract details."""
        result = tools.get_contract_details(sample_contract_spec)

        assert len(result) == 1
        assert result[0]["contract"]["symbol"] == "AAPL"
        assert result[0]["long_name"] == "Apple Inc"

    def test_search_contracts(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test searching for contracts."""
        result = tools.search_contracts("AAPL")

        assert len(result) == 1
        assert result[0]["contract"]["symbol"] == "AAPL"


class TestMarketDataTools:
    """Tests for market data tools."""

    def test_get_market_data_snapshot(
        self, tools: IBKRTools, mock_tws_client: MagicMock, sample_contract_spec: ContractSpec
    ) -> None:
        """Test getting market data snapshot."""
        result = tools.get_market_data_snapshot(sample_contract_spec)

        assert len(result) == 3
        assert result[0]["field"] == "bid"
        assert result[0]["price"] == 150.00

    def test_get_historical_data(
        self, tools: IBKRTools, mock_tws_client: MagicMock, sample_contract_spec: ContractSpec
    ) -> None:
        """Test getting historical data."""
        result = tools.get_historical_data(sample_contract_spec)

        assert len(result) == 2
        assert result[0]["open"] == 150.00
        assert result[0]["close"] == 150.75


class TestExecutionTools:
    """Tests for execution-related tools."""

    def test_get_executions(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting executions."""
        result = tools.get_executions()

        assert result == []
        mock_tws_client.get_executions.assert_called_once()


class TestPnLTools:
    """Tests for P&L tools."""

    def test_get_pnl(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting P&L."""
        result = tools.get_pnl("DU123456")

        assert result is None
        mock_tws_client.get_pnl.assert_called_once_with("DU123456", "")

    def test_get_position_pnl(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting position P&L."""
        result = tools.get_position_pnl("DU123456", 265598)

        assert result is None
        mock_tws_client.get_pnl_single.assert_called_once_with("DU123456", 265598, "")


class TestScannerTools:
    """Tests for scanner tools."""

    def test_get_scanner_parameters(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting scanner parameters."""
        result = tools.get_scanner_parameters()

        assert "<ScannerParameters>" in result
        mock_tws_client.get_scanner_parameters.assert_called_once()


class TestNewsTools:
    """Tests for news tools."""

    def test_get_news_providers(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting news providers."""
        result = tools.get_news_providers()

        assert result == []
        mock_tws_client.get_news_providers.assert_called_once()

    def test_get_historical_news(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting historical news."""
        result = tools.get_historical_news(
            con_id=265598,
            provider_codes="BZ",
            start_date_time="20240101 00:00:00",
            end_date_time="20240102 00:00:00",
        )

        assert result == []
        mock_tws_client.get_historical_news.assert_called_once()

    def test_get_news_article(self, tools: IBKRTools, mock_tws_client: MagicMock) -> None:
        """Test getting news article."""
        result = tools.get_news_article("BZ", "article123")

        assert result is None
        mock_tws_client.get_news_article.assert_called_once_with("BZ", "article123")
