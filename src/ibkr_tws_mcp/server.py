"""FastMCP server for IBKR TWS operations."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

from fastmcp import FastMCP

from .models import ContractSpec, OrderAction, OrderSpec, OrderType, SecurityType, TimeInForce
from .tools import IBKRTools
from .tws_client import TWSClientWrapper

# Initialize FastMCP server
mcp = FastMCP("ibkr-tws-mcp")

# Module logger
logger = logging.getLogger(__name__)

# Global tools instance (will be initialized with CLI args)
_tools: IBKRTools | None = None


def setup_logging() -> bool:
    """Configure logging based on DEBUG environment variable.

    Returns:
        True if debug mode is enabled
    """
    debug_mode = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
    level = logging.DEBUG if debug_mode else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    return debug_mode


def get_tools() -> IBKRTools:
    """Get the global IBKR tools instance, initializing if needed."""
    global _tools
    if _tools is None:
        # Lazy initialization with defaults from environment variables
        # Use 'or' to handle empty strings as well as None/unset
        host = os.getenv("TWS_HOST") or "127.0.0.1"
        port = int(os.getenv("TWS_PORT") or "7496")
        client_id = int(os.getenv("TWS_CLIENT_ID") or "0")
        timeout = int(os.getenv("TWS_TIMEOUT") or "30")

        logger.debug(
            f"Lazy initializing tools with: host={host}, port={port}, "
            f"client_id={client_id}, timeout={timeout}"
        )

        client = TWSClientWrapper(host=host, port=port, client_id=client_id, timeout=timeout)
        _tools = IBKRTools(client)
    return _tools


def init_tools(host: str, port: int, client_id: int, timeout: int) -> None:
    """Initialize the global tools instance with configuration.

    Args:
        host: TWS server host
        port: TWS server port
        client_id: Client ID
        timeout: Request timeout in seconds
    """
    global _tools
    logger.debug(
        f"Initializing tools with: host={host}, port={port}, "
        f"client_id={client_id}, timeout={timeout}"
    )
    client = TWSClientWrapper(host=host, port=port, client_id=client_id, timeout=timeout)
    _tools = IBKRTools(client)


# ==================== Connection Tools ====================


@mcp.tool()
def tws_connect() -> dict[str, Any]:
    """Connect to Interactive Brokers TWS/IB Gateway.

    Establishes a connection to TWS using the configured host, port, and client ID.
    Must be called before using any other TWS tools.

    Returns:
        Connection status including host, port, and client ID
    """
    return get_tools().connect()


@mcp.tool()
def tws_disconnect() -> dict[str, str]:
    """Disconnect from Interactive Brokers TWS/IB Gateway.

    Closes the connection to TWS. Call this when done using TWS tools.

    Returns:
        Disconnection status
    """
    return get_tools().disconnect()


@mcp.tool()
def tws_connection_status() -> dict[str, Any]:
    """Check the current TWS connection status.

    Returns:
        Connection status including whether connected, host, port, and client ID
    """
    return get_tools().connection_status()


@mcp.tool()
def tws_get_server_time() -> dict[str, int]:
    """Get the TWS server time.

    Returns:
        Server time as Unix timestamp
    """
    return get_tools().get_server_time()


# ==================== Account Tools ====================


@mcp.tool()
def tws_get_managed_accounts() -> list[str]:
    """Get list of managed accounts.

    Returns the account IDs that are accessible through this TWS connection.

    Returns:
        List of account IDs
    """
    return get_tools().get_managed_accounts()


@mcp.tool()
def tws_get_account_summary(
    account: str = "All",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Get account summary information.

    Retrieves account values like net liquidation, buying power, margin, etc.

    Args:
        account: Account ID or "All" for all accounts (default: "All")
        tags: List of tags to request. If not specified, returns common tags:
              NetLiquidation, TotalCashValue, BuyingPower, EquityWithLoanValue,
              GrossPositionValue, InitMarginReq, MaintMarginReq, AvailableFunds, etc.

    Returns:
        Account summary with account ID and list of tag/value pairs
    """
    return get_tools().get_account_summary(account, tags)


# ==================== Position Tools ====================


@mcp.tool()
def tws_get_positions() -> list[dict[str, Any]]:
    """Get all current positions.

    Returns positions across all accounts including symbol, quantity, average cost,
    and unrealized P&L.

    Returns:
        List of position information including account, symbol, security type,
        position size, and average cost
    """
    return get_tools().get_positions()


# ==================== Order Tools ====================


@mcp.tool()
def tws_get_open_orders() -> list[dict[str, Any]]:
    """Get open orders for this client connection.

    Returns orders that are currently open (not filled or cancelled) for this
    specific API client ID.

    Returns:
        List of open orders with order ID, contract, order details, and status
    """
    return get_tools().get_open_orders()


@mcp.tool()
def tws_get_all_open_orders() -> list[dict[str, Any]]:
    """Get all open orders across all API clients.

    Returns all open orders from all connected API clients and TWS itself.

    Returns:
        List of all open orders
    """
    return get_tools().get_all_open_orders()


@mcp.tool()
def tws_place_order(
    symbol: str,
    action: str,
    order_type: str,
    quantity: float,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    limit_price: float | None = None,
    stop_price: float | None = None,
    tif: str = "DAY",
    account: str | None = None,
    outside_rth: bool = False,
) -> dict[str, Any]:
    """Place a new order.

    Args:
        symbol: Symbol to trade (e.g., "AAPL", "MSFT")
        action: Order action - "BUY" or "SELL"
        order_type: Order type - "MKT" (market), "LMT" (limit), "STP" (stop),
                   "STP LMT" (stop-limit), "TRAIL" (trailing stop)
        quantity: Number of shares/contracts to trade
        sec_type: Security type - "STK" (stock), "OPT" (option), "FUT" (future),
                 "CASH" (forex), "CRYPTO" (cryptocurrency). Default: "STK"
        exchange: Exchange to route to. Default: "SMART"
        currency: Currency. Default: "USD"
        limit_price: Limit price for limit orders
        stop_price: Stop price for stop/stop-limit orders
        tif: Time in force - "DAY", "GTC" (good til cancelled), "IOC" (immediate
             or cancel), "FOK" (fill or kill). Default: "DAY"
        account: Account to use (required for multi-account setups)
        outside_rth: Allow trading outside regular trading hours. Default: False

    Returns:
        Order result with order ID and initial status
    """
    contract = ContractSpec(
        symbol=symbol,
        sec_type=SecurityType(sec_type),
        exchange=exchange,
        currency=currency,
    )

    order = OrderSpec(
        action=OrderAction(action),
        order_type=OrderType(order_type),
        total_quantity=quantity,
        limit_price=limit_price,
        aux_price=stop_price,
        tif=TimeInForce(tif),
        account=account,
        outside_rth=outside_rth,
    )

    return get_tools().place_order(contract, order)


@mcp.tool()
def tws_cancel_order(order_id: int) -> dict[str, Any]:
    """Cancel an open order.

    Args:
        order_id: The order ID to cancel

    Returns:
        Cancellation result with order ID and status
    """
    return get_tools().cancel_order(order_id)


@mcp.tool()
def tws_cancel_all_orders() -> dict[str, str]:
    """Cancel all open orders.

    Sends a global cancel request to cancel all open orders across all accounts.

    Returns:
        Cancellation request status
    """
    return get_tools().cancel_all_orders()


# ==================== Contract Tools ====================


@mcp.tool()
def tws_get_contract_details(
    symbol: str,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    expiry: str | None = None,
    strike: float | None = None,
    right: str | None = None,
) -> list[dict[str, Any]]:
    """Get detailed contract information.

    Retrieves full contract details including trading hours, valid exchanges,
    minimum tick size, and other specifications.

    Args:
        symbol: Symbol to look up
        sec_type: Security type - "STK", "OPT", "FUT", etc. Default: "STK"
        exchange: Exchange. Default: "SMART"
        currency: Currency. Default: "USD"
        expiry: Expiry date for options/futures (YYYYMMDD)
        strike: Strike price for options
        right: Option right - "C" for call, "P" for put

    Returns:
        List of matching contract details
    """
    contract = ContractSpec(
        symbol=symbol,
        sec_type=SecurityType(sec_type),
        exchange=exchange,
        currency=currency,
        last_trade_date_or_contract_month=expiry,
        strike=strike,
        right=right,
    )
    return get_tools().get_contract_details(contract)


@mcp.tool()
def tws_search_contracts(
    symbol: str,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
) -> list[dict[str, Any]]:
    """Search for contracts by symbol.

    Searches for contracts matching the given criteria and returns details
    for all matches.

    Args:
        symbol: Symbol to search for
        sec_type: Security type. Default: "STK"
        exchange: Exchange. Default: "SMART"
        currency: Currency. Default: "USD"

    Returns:
        List of matching contract details
    """
    return get_tools().search_contracts(symbol, sec_type, exchange, currency)


# ==================== Market Data Tools ====================


@mcp.tool()
def tws_get_market_data(
    symbol: str,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
) -> list[dict[str, Any]]:
    """Get real-time market data snapshot.

    Retrieves current market data including bid, ask, last price, volume, etc.

    Args:
        symbol: Symbol to get data for
        sec_type: Security type. Default: "STK"
        exchange: Exchange. Default: "SMART"
        currency: Currency. Default: "USD"

    Returns:
        List of tick data with prices, sizes, and attributes
    """
    contract = ContractSpec(
        symbol=symbol,
        sec_type=SecurityType(sec_type),
        exchange=exchange,
        currency=currency,
    )
    return get_tools().get_market_data_snapshot(contract)


@mcp.tool()
def tws_get_historical_data(
    symbol: str,
    duration: str = "1 D",
    bar_size: str = "1 hour",
    what_to_show: str = "TRADES",
    use_rth: bool = True,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    end_date_time: str = "",
) -> list[dict[str, Any]]:
    """Get historical price data.

    Retrieves historical OHLCV bar data for a security.

    Args:
        symbol: Symbol to get data for
        duration: Duration string - "1 D" (1 day), "1 W" (1 week), "1 M" (1 month),
                 "3 M", "6 M", "1 Y" (1 year). Default: "1 D"
        bar_size: Bar size - "1 secs", "5 secs", "1 min", "5 mins", "15 mins",
                 "30 mins", "1 hour", "4 hours", "1 day", "1 week", "1 month".
                 Default: "1 hour"
        what_to_show: Data type - "TRADES", "MIDPOINT", "BID", "ASK",
                     "BID_ASK", "ADJUSTED_LAST". Default: "TRADES"
        use_rth: Use regular trading hours only. Default: True
        sec_type: Security type. Default: "STK"
        exchange: Exchange. Default: "SMART"
        currency: Currency. Default: "USD"
        end_date_time: End date/time in format "YYYYMMDD HH:MM:SS".
                      Empty string for current time. Default: ""

    Returns:
        List of bar data with date, open, high, low, close, volume
    """
    contract = ContractSpec(
        symbol=symbol,
        sec_type=SecurityType(sec_type),
        exchange=exchange,
        currency=currency,
    )
    return get_tools().get_historical_data(
        contract=contract,
        duration=duration,
        bar_size=bar_size,
        what_to_show=what_to_show,
        use_rth=use_rth,
        end_date_time=end_date_time,
    )


# ==================== Execution Tools ====================


@mcp.tool()
def tws_get_executions(
    account: str = "",
    symbol: str = "",
    sec_type: str = "",
    side: str = "",
) -> list[dict[str, Any]]:
    """Get execution reports.

    Retrieves execution details for filled orders.

    Args:
        account: Filter by account (empty for all)
        symbol: Filter by symbol (empty for all)
        sec_type: Filter by security type (empty for all)
        side: Filter by side - "BUY" or "SELL" (empty for all)

    Returns:
        List of execution reports with order ID, symbol, price, quantity, time
    """
    return get_tools().get_executions(
        account=account,
        symbol=symbol,
        sec_type=sec_type,
        side=side,
    )


# ==================== P&L Tools ====================


@mcp.tool()
def tws_get_pnl(account: str, model_code: str = "") -> dict[str, Any] | None:
    """Get account profit and loss.

    Retrieves daily P&L, unrealized P&L, and realized P&L for an account.

    Args:
        account: Account ID
        model_code: Model code (optional, for model portfolios)

    Returns:
        P&L data with daily, unrealized, and realized P&L
    """
    return get_tools().get_pnl(account, model_code)


@mcp.tool()
def tws_get_position_pnl(account: str, con_id: int, model_code: str = "") -> dict[str, Any] | None:
    """Get position-level profit and loss.

    Retrieves P&L for a specific position identified by contract ID.

    Args:
        account: Account ID
        con_id: Contract ID of the position
        model_code: Model code (optional)

    Returns:
        Position P&L data with position size, daily/unrealized/realized P&L
    """
    return get_tools().get_position_pnl(account, con_id, model_code)


# ==================== Scanner Tools ====================


@mcp.tool()
def tws_get_scanner_parameters() -> str:
    """Get available market scanner parameters.

    Returns an XML document describing all available scanner types,
    instruments, locations, and filter parameters.

    Returns:
        Scanner parameters XML string
    """
    return get_tools().get_scanner_parameters()


# ==================== News Tools ====================


@mcp.tool()
def tws_get_news_providers() -> list[dict[str, Any]]:
    """Get list of subscribed news providers.

    Returns the news providers available for your account subscription.

    Returns:
        List of news provider information
    """
    return get_tools().get_news_providers()


@mcp.tool()
def tws_get_historical_news(
    con_id: int,
    provider_codes: str,
    start_date_time: str,
    end_date_time: str,
    total_results: int = 10,
) -> list[dict[str, Any]]:
    """Get historical news headlines.

    Retrieves news headlines for a specific contract within a date range.

    Args:
        con_id: Contract ID to get news for
        provider_codes: Comma-separated news provider codes (e.g., "BZ,FLY")
        start_date_time: Start date/time (format: "YYYYMMDD HH:MM:SS")
        end_date_time: End date/time (format: "YYYYMMDD HH:MM:SS")
        total_results: Maximum number of results. Default: 10

    Returns:
        List of news headlines with time, provider, article ID, and headline text
    """
    return get_tools().get_historical_news(
        con_id=con_id,
        provider_codes=provider_codes,
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        total_results=total_results,
    )


@mcp.tool()
def tws_get_news_article(provider_code: str, article_id: str) -> dict[str, Any] | None:
    """Get news article content.

    Retrieves the full text of a news article by its ID.

    Args:
        provider_code: News provider code
        article_id: Article ID (from historical news or real-time news)

    Returns:
        Article content with type and text, or None if not found
    """
    return get_tools().get_news_article(provider_code, article_id)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="IBKR TWS MCP Server - MCP server for Interactive Brokers TWS API"
    )

    # Use 'or' to handle empty strings as well as None/unset
    parser.add_argument(
        "--tws-host",
        type=str,
        default=os.getenv("TWS_HOST") or "127.0.0.1",
        help="TWS server host (env: TWS_HOST, default: 127.0.0.1)",
    )

    parser.add_argument(
        "--tws-port",
        type=int,
        default=int(os.getenv("TWS_PORT") or "7496"),
        help="TWS server port (env: TWS_PORT, default: 7496 for live, 7497 for paper)",
    )

    parser.add_argument(
        "--tws-client-id",
        type=int,
        default=int(os.getenv("TWS_CLIENT_ID") or "0"),
        help="TWS client ID (env: TWS_CLIENT_ID, default: 0)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("TWS_TIMEOUT") or "30"),
        help="Request timeout in seconds (env: TWS_TIMEOUT, default: 30)",
    )

    parser.add_argument(
        "--http-port",
        type=int,
        default=int(os.getenv("MCP_HTTP_PORT") or "8080"),
        help="HTTP server port (env: MCP_HTTP_PORT, default: 8080)",
    )

    parser.add_argument(
        "--http-host",
        type=str,
        default=os.getenv("MCP_HOST") or "0.0.0.0",
        help="HTTP server host (env: MCP_HOST, default: 0.0.0.0)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for the IBKR TWS MCP server."""
    # Setup logging first
    debug_mode = setup_logging()

    args = parse_args()

    logger.info(
        f"Configuration: TWS_HOST={args.tws_host}, TWS_PORT={args.tws_port}, "
        f"TWS_CLIENT_ID={args.tws_client_id}, TWS_TIMEOUT={args.timeout}"
    )

    # Initialize tools with configuration
    init_tools(
        host=args.tws_host,
        port=args.tws_port,
        client_id=args.tws_client_id,
        timeout=args.timeout,
    )

    # Auto-connect in debug mode to verify configuration
    if debug_mode:
        logger.info("Debug mode enabled - attempting automatic TWS connection...")
        try:
            result = get_tools().connect()
            logger.info(f"Auto-connect result: {result}")
        except Exception as e:
            logger.error(f"Auto-connect failed: {e}")
            # Don't exit - let the server start anyway so tools can be used

    print(
        f"Starting IBKR TWS MCP Server...\n"
        f"  TWS Host: {args.tws_host}:{args.tws_port}\n"
        f"  Client ID: {args.tws_client_id}\n"
        f"  MCP Server: http://{args.http_host}:{args.http_port}/mcp",
        file=sys.stderr,
    )

    # Run server in HTTP mode (streamable-http)
    mcp.run(transport="streamable-http", host=args.http_host, port=args.http_port)


if __name__ == "__main__":
    main()
