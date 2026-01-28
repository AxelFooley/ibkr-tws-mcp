"""Pytest fixtures for IBKR TWS MCP Server tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ibkr_tws_mcp.models import (
    AccountSummary,
    AccountSummaryItem,
    BarData,
    ContractDetails,
    ContractSpec,
    ExecutionInfo,
    OpenOrder,
    OrderSpec,
    OrderState,
    OrderStatus,
    PositionInfo,
    SecurityType,
    TickData,
)
from ibkr_tws_mcp.tools import IBKRTools
from ibkr_tws_mcp.tws_client import TWSClientWrapper


@pytest.fixture
def mock_tws_client() -> MagicMock:
    """Create a mock TWS client for testing."""
    client = MagicMock(spec=TWSClientWrapper)

    # Configure connection state
    client.host = "127.0.0.1"
    client.port = 7496
    client.client_id = 0
    client.timeout = 30
    client.is_connected.return_value = True

    # Configure mock responses
    client.get_managed_accounts.return_value = ["DU123456"]
    client.get_server_time.return_value = 1704067200

    client.get_account_summary.return_value = AccountSummary(
        account="DU123456",
        items=[
            AccountSummaryItem(tag="NetLiquidation", value="100000.00", currency="USD"),
            AccountSummaryItem(tag="TotalCashValue", value="50000.00", currency="USD"),
            AccountSummaryItem(tag="BuyingPower", value="200000.00", currency="USD"),
        ],
    )

    client.get_positions.return_value = [
        PositionInfo(
            account="DU123456",
            symbol="AAPL",
            sec_type="STK",
            exchange="SMART",
            currency="USD",
            position=100.0,
            avg_cost=150.50,
            con_id=265598,
        ),
        PositionInfo(
            account="DU123456",
            symbol="MSFT",
            sec_type="STK",
            exchange="SMART",
            currency="USD",
            position=50.0,
            avg_cost=350.25,
            con_id=272093,
        ),
    ]

    client.get_open_orders.return_value = []
    client.get_all_open_orders.return_value = []

    client.place_order_sync.return_value = (
        1,
        OrderState(
            order_id=1,
            status=OrderStatus.SUBMITTED,
            filled=0,
            remaining=100,
            avg_fill_price=0,
        ),
    )

    client.cancel_order_sync.return_value = True
    client.cancel_all_orders.return_value = True

    client.get_contract_details.return_value = [
        ContractDetails(
            contract=ContractSpec(
                symbol="AAPL",
                sec_type=SecurityType.STOCK,
                exchange="SMART",
                currency="USD",
                con_id=265598,
            ),
            long_name="Apple Inc",
            min_tick=0.01,
            valid_exchanges="SMART,AMEX,NYSE,CBOE",
        ),
    ]

    client.get_market_data_snapshot.return_value = [
        TickData(ticker_id=1, field="bid", price=150.00),
        TickData(ticker_id=1, field="ask", price=150.05),
        TickData(ticker_id=1, field="last", price=150.02),
    ]

    client.get_historical_data.return_value = [
        BarData(
            date="20240101 09:30:00",
            open=150.00,
            high=151.00,
            low=149.50,
            close=150.75,
            volume=1000000,
        ),
        BarData(
            date="20240101 10:30:00",
            open=150.75,
            high=152.00,
            low=150.50,
            close=151.50,
            volume=800000,
        ),
    ]

    client.get_executions.return_value = []

    client.get_pnl.return_value = None
    client.get_pnl_single.return_value = None

    client.get_scanner_parameters.return_value = "<ScannerParameters>...</ScannerParameters>"

    client.get_news_providers.return_value = []
    client.get_historical_news.return_value = []
    client.get_news_article.return_value = None

    client.connect_and_run.return_value = True

    return client


@pytest.fixture
def tools(mock_tws_client: MagicMock) -> IBKRTools:
    """Create IBKRTools instance with mock client."""
    return IBKRTools(mock_tws_client)


@pytest.fixture
def sample_contract_spec() -> ContractSpec:
    """Create a sample contract specification."""
    return ContractSpec(
        symbol="AAPL",
        sec_type=SecurityType.STOCK,
        exchange="SMART",
        currency="USD",
    )


@pytest.fixture
def sample_order_spec() -> OrderSpec:
    """Create a sample order specification."""
    return OrderSpec(
        action="BUY",
        order_type="LMT",
        total_quantity=100,
        limit_price=150.00,
    )
