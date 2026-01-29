"""MCP tool implementations for IBKR TWS operations."""

from __future__ import annotations

import logging
from typing import Any

from .models import (
    ContractSpec,
    OrderSpec,
    SecurityType,
)
from .tws_client import TWSClientWrapper
from .utils import create_contract, create_order

logger = logging.getLogger(__name__)


class IBKRTools:
    """IBKR TWS MCP tools implementation."""

    def __init__(self, client: TWSClientWrapper) -> None:
        """Initialize IBKR tools.

        Args:
            client: TWS client wrapper instance
        """
        self.client = client

    def ensure_connected(self) -> None:
        """Ensure connection to TWS, reconnecting if necessary.

        Raises:
            ConnectionError: If unable to connect/reconnect to TWS
        """
        if not self.client.is_connected():
            logger.info("Connection lost or not established, attempting to connect...")
            try:
                self.client.connect_and_run()
                logger.info("Connected to TWS successfully")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to TWS: {e}") from e

    # ==================== Connection Tools ====================

    def connect(self) -> dict[str, Any]:
        """Connect to TWS.

        Returns:
            Connection status information
        """
        try:
            success = self.client.connect_and_run()
            return {
                "status": "connected" if success else "failed",
                "host": self.client.host,
                "port": self.client.port,
                "client_id": self.client.client_id,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "host": self.client.host,
                "port": self.client.port,
            }

    def disconnect(self) -> dict[str, str]:
        """Disconnect from TWS.

        Returns:
            Disconnection status
        """
        self.client.disconnect_client()
        return {"status": "disconnected"}

    def connection_status(self) -> dict[str, Any]:
        """Check connection status.

        Returns:
            Connection status information
        """
        connected = self.client.is_connected()
        return {
            "connected": connected,
            "host": self.client.host,
            "port": self.client.port,
            "client_id": self.client.client_id,
        }

    def get_server_time(self) -> dict[str, int]:
        """Get TWS server time.

        Returns:
            Server time as Unix timestamp
        """
        self.ensure_connected()
        try:
            time_val = self.client.get_server_time()
            return {"server_time": time_val}
        except Exception as e:
            raise RuntimeError(f"Failed to get server time: {e}") from e

    # ==================== Account Tools ====================

    def get_managed_accounts(self) -> list[str]:
        """Get list of managed accounts.

        Returns:
            List of account IDs
        """
        self.ensure_connected()
        return self.client.get_managed_accounts()

    def get_account_summary(
        self, account: str = "All", tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Get account summary.

        Args:
            account: Account ID or "All" for all accounts
            tags: List of tags to request (defaults to common tags)

        Returns:
            Account summary data
        """
        self.ensure_connected()
        try:
            summary = self.client.get_account_summary(account, tags)
            return summary.model_dump()
        except Exception as e:
            raise RuntimeError(f"Failed to get account summary: {e}") from e

    # ==================== Position Tools ====================

    def get_positions(self) -> list[dict[str, Any]]:
        """Get all positions.

        Returns:
            List of position information
        """
        self.ensure_connected()
        try:
            positions = self.client.get_positions()
            return [pos.model_dump() for pos in positions]
        except Exception as e:
            raise RuntimeError(f"Failed to get positions: {e}") from e

    # ==================== Order Tools ====================

    def get_open_orders(self) -> list[dict[str, Any]]:
        """Get open orders for this client.

        Returns:
            List of open orders
        """
        self.ensure_connected()
        try:
            orders = self.client.get_open_orders()
            return [order.model_dump() for order in orders]
        except Exception as e:
            raise RuntimeError(f"Failed to get open orders: {e}") from e

    def get_all_open_orders(self) -> list[dict[str, Any]]:
        """Get all open orders across all clients.

        Returns:
            List of open orders
        """
        self.ensure_connected()
        try:
            orders = self.client.get_all_open_orders()
            return [order.model_dump() for order in orders]
        except Exception as e:
            raise RuntimeError(f"Failed to get all open orders: {e}") from e

    def place_order(self, contract: ContractSpec, order: OrderSpec) -> dict[str, Any]:
        """Place an order.

        Args:
            contract: Contract specification
            order: Order specification

        Returns:
            Order placement result with order ID
        """
        self.ensure_connected()
        try:
            ib_contract = create_contract(contract)
            ib_order = create_order(order)

            order_id, state = self.client.place_order_sync(ib_contract, ib_order)

            result: dict[str, Any] = {
                "order_id": order_id,
                "status": "submitted",
            }

            if state:
                result["order_state"] = state.model_dump()

            return result
        except Exception as e:
            raise RuntimeError(f"Failed to place order: {e}") from e

    def cancel_order(self, order_id: int) -> dict[str, Any]:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation result
        """
        self.ensure_connected()
        try:
            success = self.client.cancel_order_sync(order_id)
            return {
                "order_id": order_id,
                "status": "cancel_requested" if success else "failed",
            }
        except Exception as e:
            raise RuntimeError(f"Failed to cancel order: {e}") from e

    def cancel_all_orders(self) -> dict[str, str]:
        """Cancel all open orders.

        Returns:
            Cancellation result
        """
        self.ensure_connected()
        try:
            success = self.client.cancel_all_orders()
            return {"status": "cancel_all_requested" if success else "failed"}
        except Exception as e:
            raise RuntimeError(f"Failed to cancel all orders: {e}") from e

    # ==================== Contract Tools ====================

    def get_contract_details(self, contract: ContractSpec) -> list[dict[str, Any]]:
        """Get contract details.

        Args:
            contract: Contract specification

        Returns:
            List of matching contract details
        """
        self.ensure_connected()
        try:
            ib_contract = create_contract(contract)
            details = self.client.get_contract_details(ib_contract)
            return [d.model_dump() for d in details]
        except Exception as e:
            raise RuntimeError(f"Failed to get contract details: {e}") from e

    def search_contracts(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Search for contracts by symbol.

        Args:
            symbol: Symbol to search for
            sec_type: Security type (default: STK)
            exchange: Exchange (default: SMART)
            currency: Currency (default: USD)

        Returns:
            List of matching contract details
        """
        spec = ContractSpec(
            symbol=symbol,
            sec_type=SecurityType(sec_type),
            exchange=exchange,
            currency=currency,
        )
        return self.get_contract_details(spec)

    # ==================== Market Data Tools ====================

    def get_market_data_snapshot(
        self,
        contract: ContractSpec,
        generic_tick_list: str = "",
    ) -> list[dict[str, Any]]:
        """Get market data snapshot.

        Args:
            contract: Contract specification
            generic_tick_list: Comma-separated generic tick types

        Returns:
            List of tick data
        """
        self.ensure_connected()
        try:
            ib_contract = create_contract(contract)
            ticks = self.client.get_market_data_snapshot(ib_contract, generic_tick_list)
            return [tick.model_dump() for tick in ticks]
        except Exception as e:
            raise RuntimeError(f"Failed to get market data: {e}") from e

    def get_historical_data(
        self,
        contract: ContractSpec,
        duration: str = "1 D",
        bar_size: str = "1 hour",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        end_date_time: str = "",
    ) -> list[dict[str, Any]]:
        """Get historical bar data.

        Args:
            contract: Contract specification
            duration: Duration string (e.g., "1 D", "1 W", "1 M", "1 Y")
            bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
            what_to_show: Data type (TRADES, MIDPOINT, BID, ASK)
            use_rth: Use regular trading hours only
            end_date_time: End date/time (empty string for now)

        Returns:
            List of bar data
        """
        self.ensure_connected()
        try:
            ib_contract = create_contract(contract)
            bars = self.client.get_historical_data(
                contract=ib_contract,
                end_date_time=end_date_time,
                duration=duration,
                bar_size=bar_size,
                what_to_show=what_to_show,
                use_rth=use_rth,
            )
            return [bar.model_dump() for bar in bars]
        except Exception as e:
            raise RuntimeError(f"Failed to get historical data: {e}") from e

    # ==================== Execution Tools ====================

    def get_executions(
        self,
        client_id: int = 0,
        account: str = "",
        symbol: str = "",
        sec_type: str = "",
        exchange: str = "",
        side: str = "",
    ) -> list[dict[str, Any]]:
        """Get execution reports.

        Args:
            client_id: Filter by client ID (0 for all)
            account: Filter by account
            symbol: Filter by symbol
            sec_type: Filter by security type
            exchange: Filter by exchange
            side: Filter by side (BUY/SELL)

        Returns:
            List of execution reports
        """
        self.ensure_connected()
        try:
            executions = self.client.get_executions(
                client_id=client_id,
                account=account,
                symbol=symbol,
                sec_type=sec_type,
                exchange=exchange,
                side=side,
            )
            return [e.model_dump() for e in executions]
        except Exception as e:
            raise RuntimeError(f"Failed to get executions: {e}") from e

    # ==================== P&L Tools ====================

    def get_pnl(self, account: str, model_code: str = "") -> dict[str, Any] | None:
        """Get account P&L.

        Args:
            account: Account ID
            model_code: Model code (optional)

        Returns:
            P&L data or None
        """
        self.ensure_connected()
        try:
            pnl = self.client.get_pnl(account, model_code)
            return pnl.model_dump() if pnl else None
        except Exception as e:
            raise RuntimeError(f"Failed to get P&L: {e}") from e

    def get_position_pnl(
        self, account: str, con_id: int, model_code: str = ""
    ) -> dict[str, Any] | None:
        """Get position-level P&L.

        Args:
            account: Account ID
            con_id: Contract ID
            model_code: Model code (optional)

        Returns:
            Position P&L data or None
        """
        self.ensure_connected()
        try:
            pnl = self.client.get_pnl_single(account, con_id, model_code)
            return pnl.model_dump() if pnl else None
        except Exception as e:
            raise RuntimeError(f"Failed to get position P&L: {e}") from e

    # ==================== Scanner Tools ====================

    def get_scanner_parameters(self) -> str:
        """Get available scanner parameters XML.

        Returns:
            Scanner parameters XML string
        """
        self.ensure_connected()
        try:
            return self.client.get_scanner_parameters()
        except Exception as e:
            raise RuntimeError(f"Failed to get scanner parameters: {e}") from e

    # ==================== News Tools ====================

    def get_news_providers(self) -> list[dict[str, Any]]:
        """Get list of news providers.

        Returns:
            List of news provider information
        """
        self.ensure_connected()
        try:
            providers = self.client.get_news_providers()
            # Convert to list of dicts if needed
            if providers and hasattr(providers[0], "__dict__"):
                return [vars(p) for p in providers]
            return providers
        except Exception as e:
            raise RuntimeError(f"Failed to get news providers: {e}") from e

    def get_historical_news(
        self,
        con_id: int,
        provider_codes: str,
        start_date_time: str,
        end_date_time: str,
        total_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Get historical news headlines.

        Args:
            con_id: Contract ID
            provider_codes: Comma-separated provider codes
            start_date_time: Start date/time (yyyyMMdd HH:mm:ss)
            end_date_time: End date/time (yyyyMMdd HH:mm:ss)
            total_results: Maximum number of results

        Returns:
            List of news headlines
        """
        self.ensure_connected()
        try:
            headlines = self.client.get_historical_news(
                con_id=con_id,
                provider_codes=provider_codes,
                start_date_time=start_date_time,
                end_date_time=end_date_time,
                total_results=total_results,
            )
            return [h.model_dump() for h in headlines]
        except Exception as e:
            raise RuntimeError(f"Failed to get historical news: {e}") from e

    def get_news_article(self, provider_code: str, article_id: str) -> dict[str, Any] | None:
        """Get news article content.

        Args:
            provider_code: News provider code
            article_id: Article ID

        Returns:
            Article content or None
        """
        self.ensure_connected()
        try:
            return self.client.get_news_article(provider_code, article_id)
        except Exception as e:
            raise RuntimeError(f"Failed to get news article: {e}") from e
