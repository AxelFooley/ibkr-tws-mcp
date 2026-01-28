"""TWS Client wrapper for synchronous operations over ibapi."""

from __future__ import annotations

import logging
import threading
import time
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any

from ibapi.client import EClient
from ibapi.common import BarData as IBBarData
from ibapi.common import TickAttrib, TickerId
from ibapi.contract import Contract
from ibapi.contract import ContractDetails as IBContractDetails
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState as IBOrderState
from ibapi.wrapper import EWrapper

from .models import (
    AccountSummary,
    AccountSummaryItem,
    BarData,
    CommissionReport,
    ContractDetails,
    ContractSpec,
    ExecutionInfo,
    NewsHeadline,
    OpenOrder,
    OrderSpec,
    OrderState,
    OrderStatus,
    PnLData,
    PnLSingleData,
    PositionInfo,
    ScannerResult,
    SecurityType,
    TickData,
)

if TYPE_CHECKING:
    from ibapi.commission_report import CommissionReport as IBCommissionReport

logger = logging.getLogger(__name__)


class TWSClientWrapper(EWrapper, EClient):
    """Synchronous wrapper for TWS ibapi client.

    This class combines EClient and EWrapper to provide synchronous methods
    for TWS API operations. It uses queues to collect callback responses
    and blocks until responses are received or timeout occurs.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7496,
        client_id: int = 0,
        timeout: int = 30,
    ) -> None:
        """Initialize TWS client wrapper.

        Args:
            host: TWS host address
            port: TWS port (7496 for live, 7497 for paper)
            client_id: Unique client ID (0-32)
            timeout: Default timeout for requests in seconds
        """
        EWrapper.__init__(self)
        EClient.__init__(self, self)

        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout

        # Connection state
        self._connected = False
        self._next_valid_id: int | None = None
        self._managed_accounts: list[str] = []
        self._connection_event = threading.Event()

        # Request ID counter
        self._req_id_counter = 0
        self._req_id_lock = threading.Lock()

        # Response queues keyed by request ID
        self._response_queues: dict[int, Queue[Any]] = {}
        self._response_locks: dict[int, threading.Lock] = {}

        # Special queues for different response types
        self._positions_queue: Queue[PositionInfo | None] = Queue()
        self._open_orders_queue: Queue[OpenOrder | None] = Queue()
        self._executions_queue: Queue[ExecutionInfo | None] = Queue()
        self._account_updates_queue: Queue[tuple[str, str, str, str] | None] = Queue()
        self._commission_reports_queue: Queue[CommissionReport | None] = Queue()

        # Error tracking
        self._last_error: tuple[int, int, str] | None = None
        self._error_queue: Queue[tuple[int, int, str]] = Queue()

    def _get_next_req_id(self) -> int:
        """Get next request ID."""
        with self._req_id_lock:
            self._req_id_counter += 1
            return self._req_id_counter

    def _create_response_queue(self, req_id: int) -> Queue[Any]:
        """Create a response queue for a request ID."""
        queue: Queue[Any] = Queue()
        self._response_queues[req_id] = queue
        self._response_locks[req_id] = threading.Lock()
        return queue

    def _cleanup_response_queue(self, req_id: int) -> None:
        """Clean up response queue after request completes."""
        self._response_queues.pop(req_id, None)
        self._response_locks.pop(req_id, None)

    def _wait_for_response(
        self,
        queue: Queue[Any],
        timeout: int | None = None,
        end_marker: Any = None,
        collect_all: bool = False,
    ) -> Any:
        """Wait for response from queue.

        Args:
            queue: Queue to wait on
            timeout: Timeout in seconds (uses default if None)
            end_marker: Marker indicating end of responses
            collect_all: Whether to collect all responses until end marker

        Returns:
            Single response or list of responses if collect_all is True
        """
        timeout = timeout or self.timeout
        deadline = time.time() + timeout
        results: list[Any] = []

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                if collect_all and results:
                    return results
                raise TimeoutError(f"Request timed out after {timeout} seconds")

            try:
                item = queue.get(timeout=min(remaining, 1.0))

                if item is end_marker or (end_marker is None and item is None):
                    return results if collect_all else item

                if collect_all:
                    results.append(item)
                else:
                    return item

            except Empty:
                # Check for errors
                if not self._error_queue.empty():
                    try:
                        error = self._error_queue.get_nowait()
                        if error[1] not in (2104, 2106, 2158):  # Info messages
                            raise RuntimeError(f"TWS Error {error[1]}: {error[2]}")
                    except Empty:
                        pass
                continue

    # ==================== Connection Methods ====================

    def connect_and_run(self) -> bool:
        """Connect to TWS and start message processing.

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        try:
            self.connect(self.host, self.port, self.client_id)

            # Start message processing thread
            thread = threading.Thread(target=self.run, daemon=True)
            thread.start()

            # Wait for connection confirmation
            if not self._connection_event.wait(timeout=self.timeout):
                raise TimeoutError("Connection to TWS timed out")

            self._connected = True
            logger.info(
                f"Connected to TWS at {self.host}:{self.port} with client ID {self.client_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to TWS: {e}")
            self._connected = False
            raise

    def disconnect_client(self) -> None:
        """Disconnect from TWS."""
        if self._connected:
            self.disconnect()
            self._connected = False
            self._connection_event.clear()
            logger.info("Disconnected from TWS")

    def is_connected(self) -> bool:
        """Check if connected to TWS."""
        return self._connected and self.isConnected()

    # ==================== EWrapper Callbacks ====================

    def nextValidId(self, orderId: int) -> None:
        """Callback for next valid order ID - indicates successful connection."""
        self._next_valid_id = orderId
        self._connection_event.set()
        logger.debug(f"Received next valid order ID: {orderId}")

    def managedAccounts(self, accountsList: str) -> None:
        """Callback for managed accounts list."""
        self._managed_accounts = [a.strip() for a in accountsList.split(",") if a.strip()]
        logger.debug(f"Managed accounts: {self._managed_accounts}")

    def error(
        self,
        reqId: TickerId,
        errorCode: int,
        errorString: str,
        advancedOrderRejectJson: str = "",
    ) -> None:
        """Callback for error messages."""
        self._last_error = (reqId, errorCode, errorString)
        self._error_queue.put((reqId, errorCode, errorString))

        # Log based on severity
        if errorCode in (2104, 2106, 2158):  # Info messages
            logger.debug(f"TWS Info [{errorCode}]: {errorString}")
        elif errorCode < 1000:  # System errors
            logger.error(f"TWS System Error [{errorCode}]: {errorString}")
        elif errorCode < 2000:  # Warning
            logger.warning(f"TWS Warning [{errorCode}]: {errorString}")
        else:
            logger.info(f"TWS Message [{errorCode}]: {errorString}")

        # Put error in request queue if applicable
        if reqId in self._response_queues:
            self._response_queues[reqId].put(("ERROR", errorCode, errorString))

    def currentTime(self, time_val: int) -> None:
        """Callback for server time."""
        for queue in self._response_queues.values():
            queue.put(time_val)

    # ==================== Account Callbacks ====================

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str) -> None:
        """Callback for account summary data."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put((account, tag, value, currency))

    def accountSummaryEnd(self, reqId: int) -> None:
        """Callback for end of account summary."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(None)

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str) -> None:
        """Callback for account value updates."""
        self._account_updates_queue.put((key, val, currency, accountName))

    def updateAccountTime(self, timeStamp: str) -> None:
        """Callback for account update time."""
        logger.debug(f"Account update time: {timeStamp}")

    def accountDownloadEnd(self, accountName: str) -> None:
        """Callback for end of account download."""
        self._account_updates_queue.put(None)

    # ==================== Position Callbacks ====================

    def position(self, account: str, contract: Contract, position: float, avgCost: float) -> None:
        """Callback for position data."""
        pos_info = PositionInfo(
            account=account,
            symbol=contract.symbol,
            sec_type=contract.secType,
            exchange=contract.exchange or "SMART",
            currency=contract.currency,
            position=position,
            avg_cost=avgCost,
            con_id=contract.conId,
        )
        self._positions_queue.put(pos_info)

    def positionEnd(self) -> None:
        """Callback for end of positions."""
        self._positions_queue.put(None)

    # ==================== Order Callbacks ====================

    def openOrder(
        self,
        orderId: int,
        contract: Contract,
        order: Order,
        orderState: IBOrderState,
    ) -> None:
        """Callback for open order data."""
        contract_spec = ContractSpec(
            symbol=contract.symbol,
            sec_type=SecurityType(contract.secType) if contract.secType else SecurityType.STOCK,
            exchange=contract.exchange or "SMART",
            currency=contract.currency or "USD",
            con_id=contract.conId,
        )

        order_spec = OrderSpec(
            action=order.action,
            order_type=order.orderType,
            total_quantity=order.totalQuantity,
            limit_price=order.lmtPrice if order.lmtPrice != 0 else None,
            aux_price=order.auxPrice if order.auxPrice != 0 else None,
            tif=order.tif,
            account=order.account,
            transmit=order.transmit,
        )

        state = OrderState(
            order_id=orderId,
            status=OrderStatus(orderState.status) if orderState.status else OrderStatus.SUBMITTED,
            filled=0,
            remaining=order.totalQuantity,
            avg_fill_price=0,
            perm_id=order.permId,
        )

        open_order = OpenOrder(
            order_id=orderId,
            contract=contract_spec,
            order=order_spec,
            order_state=state,
        )
        self._open_orders_queue.put(open_order)

    def openOrderEnd(self) -> None:
        """Callback for end of open orders."""
        self._open_orders_queue.put(None)

    def orderStatus(
        self,
        orderId: int,
        status: str,
        filled: float,
        remaining: float,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float,
    ) -> None:
        """Callback for order status updates."""
        for queue in self._response_queues.values():
            queue.put(
                OrderState(
                    order_id=orderId,
                    status=OrderStatus(status) if status else OrderStatus.SUBMITTED,
                    filled=filled,
                    remaining=remaining,
                    avg_fill_price=avgFillPrice,
                    last_fill_price=lastFillPrice,
                    perm_id=permId,
                    parent_id=parentId,
                    client_id=clientId,
                    why_held=whyHeld,
                    mkt_cap_price=mktCapPrice,
                )
            )

    # ==================== Execution Callbacks ====================

    def execDetails(self, reqId: int, contract: Contract, execution: Execution) -> None:
        """Callback for execution details."""
        exec_info = ExecutionInfo(
            exec_id=execution.execId,
            order_id=execution.orderId,
            account=execution.acctNumber,
            symbol=contract.symbol,
            sec_type=contract.secType,
            exchange=execution.exchange,
            side=execution.side,
            shares=execution.shares,
            price=execution.price,
            perm_id=execution.permId,
            client_id=execution.clientId,
            liquidation=execution.liquidation,
            cum_qty=execution.cumQty,
            avg_price=execution.avgPrice,
            order_ref=execution.orderRef or "",
            ev_rule=execution.evRule or "",
            ev_multiplier=execution.evMultiplier,
            model_code=execution.modelCode or "",
            last_liquidity=execution.lastLiquidity,
            time=execution.time,
        )
        self._executions_queue.put(exec_info)

    def execDetailsEnd(self, reqId: int) -> None:
        """Callback for end of executions."""
        self._executions_queue.put(None)

    def commissionReport(self, commissionReport: IBCommissionReport) -> None:
        """Callback for commission report."""
        report = CommissionReport(
            exec_id=commissionReport.execId,
            commission=commissionReport.commission,
            currency=commissionReport.currency,
            realized_pnl=commissionReport.realizedPNL,
            yield_value=commissionReport.yield_,
            yield_redemption_date=str(commissionReport.yieldRedemptionDate)
            if commissionReport.yieldRedemptionDate
            else "",
        )
        self._commission_reports_queue.put(report)

    # ==================== Contract Callbacks ====================

    def contractDetails(self, reqId: int, contractDetails: IBContractDetails) -> None:
        """Callback for contract details."""
        if reqId in self._response_queues:
            contract = contractDetails.contract
            details = ContractDetails(
                contract=ContractSpec(
                    symbol=contract.symbol,
                    sec_type=SecurityType(contract.secType)
                    if contract.secType
                    else SecurityType.STOCK,
                    exchange=contract.exchange or "SMART",
                    currency=contract.currency or "USD",
                    con_id=contract.conId,
                    last_trade_date_or_contract_month=contract.lastTradeDateOrContractMonth,
                    strike=contract.strike if contract.strike else None,
                    right=contract.right if contract.right else None,
                    multiplier=contract.multiplier if contract.multiplier else None,
                    local_symbol=contract.localSymbol,
                    primary_exchange=contract.primaryExchange,
                    trading_class=contract.tradingClass,
                ),
                market_name=contractDetails.marketName or "",
                min_tick=contractDetails.minTick,
                price_magnifier=contractDetails.priceMagnifier,
                order_types=contractDetails.orderTypes or "",
                valid_exchanges=contractDetails.validExchanges or "",
                under_con_id=contractDetails.underConId,
                long_name=contractDetails.longName or "",
                contract_month=contractDetails.contractMonth or "",
                industry=contractDetails.industry or "",
                category=contractDetails.category or "",
                subcategory=contractDetails.subcategory or "",
                time_zone_id=contractDetails.timeZoneId or "",
                trading_hours=contractDetails.tradingHours or "",
                liquid_hours=contractDetails.liquidHours or "",
                ev_rule=contractDetails.evRule or "",
                ev_multiplier=contractDetails.evMultiplier,
            )
            self._response_queues[reqId].put(details)

    def contractDetailsEnd(self, reqId: int) -> None:
        """Callback for end of contract details."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(None)

    # ==================== Market Data Callbacks ====================

    def tickPrice(self, reqId: TickerId, tickType: int, price: float, attrib: TickAttrib) -> None:
        """Callback for price ticks."""
        tick_fields = {
            1: "bid",
            2: "ask",
            4: "last",
            6: "high",
            7: "low",
            9: "close",
            14: "open",
        }
        field = tick_fields.get(tickType, f"price_{tickType}")

        if reqId in self._response_queues:
            self._response_queues[reqId].put(
                TickData(
                    ticker_id=reqId,
                    field=field,
                    price=price,
                    attribs={
                        "canAutoExecute": attrib.canAutoExecute,
                        "pastLimit": attrib.pastLimit,
                        "preOpen": attrib.preOpen,
                    },
                )
            )

    def tickSize(self, reqId: TickerId, tickType: int, size: int) -> None:
        """Callback for size ticks."""
        size_fields = {0: "bid_size", 3: "ask_size", 5: "last_size", 8: "volume"}
        field = size_fields.get(tickType, f"size_{tickType}")

        if reqId in self._response_queues:
            self._response_queues[reqId].put(TickData(ticker_id=reqId, field=field, size=size))

    def tickSnapshotEnd(self, reqId: int) -> None:
        """Callback for end of snapshot."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(None)

    # ==================== Historical Data Callbacks ====================

    def historicalData(self, reqId: int, bar: IBBarData) -> None:
        """Callback for historical data."""
        if reqId in self._response_queues:
            bar_data = BarData(
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=int(bar.volume),
                wap=bar.wap if hasattr(bar, "wap") else 0.0,
                bar_count=bar.barCount if hasattr(bar, "barCount") else 0,
            )
            self._response_queues[reqId].put(bar_data)

    def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:
        """Callback for end of historical data."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(None)

    # ==================== P&L Callbacks ====================

    def pnl(self, reqId: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float) -> None:
        """Callback for P&L data."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(
                PnLData(
                    account="",
                    daily_pnl=dailyPnL,
                    unrealized_pnl=unrealizedPnL,
                    realized_pnl=realizedPnL,
                )
            )

    def pnlSingle(
        self,
        reqId: int,
        pos: float,
        dailyPnL: float,
        unrealizedPnL: float,
        realizedPnL: float,
        value: float,
    ) -> None:
        """Callback for single position P&L."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(
                PnLSingleData(
                    account="",
                    con_id=0,
                    position=pos,
                    daily_pnl=dailyPnL,
                    unrealized_pnl=unrealizedPnL,
                    realized_pnl=realizedPnL,
                    value=value,
                )
            )

    # ==================== Scanner Callbacks ====================

    def scannerParameters(self, xml: str) -> None:
        """Callback for scanner parameters XML."""
        for queue in self._response_queues.values():
            queue.put(xml)

    def scannerData(
        self,
        reqId: int,
        rank: int,
        contractDetails: IBContractDetails,
        distance: str,
        benchmark: str,
        projection: str,
        legsStr: str,
    ) -> None:
        """Callback for scanner data."""
        if reqId in self._response_queues:
            contract = contractDetails.contract
            result = ScannerResult(
                rank=rank,
                contract=ContractSpec(
                    symbol=contract.symbol,
                    sec_type=SecurityType(contract.secType)
                    if contract.secType
                    else SecurityType.STOCK,
                    exchange=contract.exchange or "SMART",
                    currency=contract.currency or "USD",
                    con_id=contract.conId,
                ),
                distance=distance,
                benchmark=benchmark,
                projection=projection,
                legs_str=legsStr,
            )
            self._response_queues[reqId].put(result)

    def scannerDataEnd(self, reqId: int) -> None:
        """Callback for end of scanner data."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(None)

    # ==================== News Callbacks ====================

    def newsProviders(self, newsProviders: list[Any]) -> None:
        """Callback for news providers."""
        for queue in self._response_queues.values():
            queue.put(newsProviders)

    def historicalNews(
        self,
        reqId: int,
        time_val: str,
        providerCode: str,
        articleId: str,
        headline: str,
    ) -> None:
        """Callback for historical news."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(
                NewsHeadline(
                    time=time_val,
                    provider_code=providerCode,
                    article_id=articleId,
                    headline=headline,
                )
            )

    def historicalNewsEnd(self, reqId: int, hasMore: bool) -> None:
        """Callback for end of historical news."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put(None)

    def newsArticle(self, reqId: int, articleType: int, articleText: str) -> None:
        """Callback for news article content."""
        if reqId in self._response_queues:
            self._response_queues[reqId].put({"type": articleType, "text": articleText})

    # ==================== Synchronous API Methods ====================

    def get_server_time(self) -> int:
        """Get TWS server time.

        Returns:
            Server time as Unix timestamp
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqCurrentTime()
            result = self._wait_for_response(queue)
            return int(result)
        finally:
            self._cleanup_response_queue(req_id)

    def get_managed_accounts(self) -> list[str]:
        """Get list of managed accounts.

        Returns:
            List of account IDs
        """
        return self._managed_accounts.copy()

    def get_next_order_id(self) -> int:
        """Get next valid order ID.

        Returns:
            Next valid order ID
        """
        if self._next_valid_id is None:
            raise RuntimeError("Not connected to TWS")
        order_id = self._next_valid_id
        self._next_valid_id += 1
        return order_id

    def get_account_summary(
        self, account: str = "All", tags: list[str] | None = None
    ) -> AccountSummary:
        """Get account summary.

        Args:
            account: Account ID or "All" for all accounts
            tags: List of tags to request (defaults to common tags)

        Returns:
            AccountSummary with requested data
        """
        if tags is None:
            tags = [
                "NetLiquidation",
                "TotalCashValue",
                "SettledCash",
                "AccruedCash",
                "BuyingPower",
                "EquityWithLoanValue",
                "GrossPositionValue",
                "RegTEquity",
                "RegTMargin",
                "InitMarginReq",
                "MaintMarginReq",
                "AvailableFunds",
                "ExcessLiquidity",
                "Cushion",
            ]

        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqAccountSummary(req_id, account, ",".join(tags))
            responses = self._wait_for_response(queue, collect_all=True)

            # Group by account
            accounts: dict[str, list[AccountSummaryItem]] = {}
            for resp in responses:
                if isinstance(resp, tuple) and len(resp) == 4:
                    acct, tag, value, currency = resp
                    if acct not in accounts:
                        accounts[acct] = []
                    accounts[acct].append(
                        AccountSummaryItem(tag=tag, value=value, currency=currency)
                    )

            # Return first account summary (or specified account)
            if account != "All" and account in accounts:
                return AccountSummary(account=account, items=accounts[account])
            elif accounts:
                first_account = next(iter(accounts))
                return AccountSummary(account=first_account, items=accounts[first_account])
            else:
                return AccountSummary(account=account, items=[])

        finally:
            self.cancelAccountSummary(req_id)
            self._cleanup_response_queue(req_id)

    def get_positions(self) -> list[PositionInfo]:
        """Get all positions.

        Returns:
            List of position information
        """
        # Clear queue
        while not self._positions_queue.empty():
            try:
                self._positions_queue.get_nowait()
            except Empty:
                break

        self.reqPositions()

        positions: list[PositionInfo] = []
        deadline = time.time() + self.timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            try:
                item = self._positions_queue.get(timeout=min(remaining, 1.0))
                if item is None:
                    break
                positions.append(item)
            except Empty:
                continue

        return positions

    def get_open_orders(self) -> list[OpenOrder]:
        """Get all open orders for this client.

        Returns:
            List of open orders
        """
        # Clear queue
        while not self._open_orders_queue.empty():
            try:
                self._open_orders_queue.get_nowait()
            except Empty:
                break

        self.reqOpenOrders()

        orders: list[OpenOrder] = []
        deadline = time.time() + self.timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            try:
                item = self._open_orders_queue.get(timeout=min(remaining, 1.0))
                if item is None:
                    break
                orders.append(item)
            except Empty:
                continue

        return orders

    def get_all_open_orders(self) -> list[OpenOrder]:
        """Get all open orders across all clients.

        Returns:
            List of open orders
        """
        # Clear queue
        while not self._open_orders_queue.empty():
            try:
                self._open_orders_queue.get_nowait()
            except Empty:
                break

        self.reqAllOpenOrders()

        orders: list[OpenOrder] = []
        deadline = time.time() + self.timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            try:
                item = self._open_orders_queue.get(timeout=min(remaining, 1.0))
                if item is None:
                    break
                orders.append(item)
            except Empty:
                continue

        return orders

    def place_order_sync(self, contract: Contract, order: Order) -> tuple[int, OrderState | None]:
        """Place an order and wait for initial status.

        Args:
            contract: Contract to trade
            order: Order specification

        Returns:
            Tuple of (order_id, order_state)
        """
        order_id = self.get_next_order_id()
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.placeOrder(order_id, contract, order)

            # Wait for initial order status
            try:
                response = self._wait_for_response(queue, timeout=5)
                if isinstance(response, OrderState):
                    return (order_id, response)
            except TimeoutError:
                pass

            return (order_id, None)
        finally:
            self._cleanup_response_queue(req_id)

    def cancel_order_sync(self, order_id: int) -> bool:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancel request sent
        """
        self.cancelOrder(order_id, "")
        return True

    def cancel_all_orders(self) -> bool:
        """Cancel all open orders.

        Returns:
            True if cancel request sent
        """
        self.reqGlobalCancel()
        return True

    def get_contract_details(self, contract: Contract) -> list[ContractDetails]:
        """Get contract details.

        Args:
            contract: Contract to look up

        Returns:
            List of matching contract details
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqContractDetails(req_id, contract)
            responses = self._wait_for_response(queue, collect_all=True)
            return [r for r in responses if isinstance(r, ContractDetails)]
        finally:
            self._cleanup_response_queue(req_id)

    def get_historical_data(
        self,
        contract: Contract,
        end_date_time: str = "",
        duration: str = "1 D",
        bar_size: str = "1 hour",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        format_date: int = 1,
    ) -> list[BarData]:
        """Get historical data.

        Args:
            contract: Contract to get data for
            end_date_time: End date/time (empty for now)
            duration: Duration string (e.g., "1 D", "1 W", "1 M")
            bar_size: Bar size (e.g., "1 min", "1 hour", "1 day")
            what_to_show: Data type (TRADES, MIDPOINT, BID, ASK)
            use_rth: Use regular trading hours only
            format_date: Date format (1 = yyyyMMdd HH:mm:ss, 2 = Unix timestamp)

        Returns:
            List of bar data
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqHistoricalData(
                req_id,
                contract,
                end_date_time,
                duration,
                bar_size,
                what_to_show,
                use_rth,
                format_date,
                False,  # keepUpToDate
                [],  # chartOptions
            )
            responses = self._wait_for_response(queue, collect_all=True)
            return [r for r in responses if isinstance(r, BarData)]
        finally:
            self._cleanup_response_queue(req_id)

    def get_market_data_snapshot(
        self, contract: Contract, generic_tick_list: str = ""
    ) -> list[TickData]:
        """Get market data snapshot.

        Args:
            contract: Contract to get data for
            generic_tick_list: Comma-separated list of generic tick types

        Returns:
            List of tick data
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqMktData(
                req_id,
                contract,
                generic_tick_list,
                True,  # snapshot
                False,  # regulatorySnapshot
                [],  # mktDataOptions
            )
            responses = self._wait_for_response(queue, collect_all=True, timeout=10)
            return [r for r in responses if isinstance(r, TickData)]
        finally:
            self.cancelMktData(req_id)
            self._cleanup_response_queue(req_id)

    def get_executions(
        self,
        client_id: int = 0,
        account: str = "",
        time_filter: str = "",
        symbol: str = "",
        sec_type: str = "",
        exchange: str = "",
        side: str = "",
    ) -> list[ExecutionInfo]:
        """Get execution reports.

        Args:
            client_id: Filter by client ID (0 for all)
            account: Filter by account
            time_filter: Filter by time (yyyymmdd hh:mm:ss)
            symbol: Filter by symbol
            sec_type: Filter by security type
            exchange: Filter by exchange
            side: Filter by side (BUY/SELL)

        Returns:
            List of execution info
        """
        # Clear queue
        while not self._executions_queue.empty():
            try:
                self._executions_queue.get_nowait()
            except Empty:
                break

        exec_filter = ExecutionFilter()
        exec_filter.clientId = client_id
        exec_filter.acctCode = account
        exec_filter.time = time_filter
        exec_filter.symbol = symbol
        exec_filter.secType = sec_type
        exec_filter.exchange = exchange
        exec_filter.side = side

        req_id = self._get_next_req_id()
        self.reqExecutions(req_id, exec_filter)

        executions: list[ExecutionInfo] = []
        deadline = time.time() + self.timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            try:
                item = self._executions_queue.get(timeout=min(remaining, 1.0))
                if item is None:
                    break
                executions.append(item)
            except Empty:
                continue

        return executions

    def get_pnl(self, account: str, model_code: str = "") -> PnLData | None:
        """Get account P&L.

        Args:
            account: Account ID
            model_code: Model code (optional)

        Returns:
            P&L data or None
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqPnL(req_id, account, model_code)
            response = self._wait_for_response(queue, timeout=10)
            if isinstance(response, PnLData):
                response.account = account
                response.model_code = model_code
                return response
            return None
        finally:
            self.cancelPnL(req_id)
            self._cleanup_response_queue(req_id)

    def get_pnl_single(
        self, account: str, con_id: int, model_code: str = ""
    ) -> PnLSingleData | None:
        """Get position P&L.

        Args:
            account: Account ID
            con_id: Contract ID
            model_code: Model code (optional)

        Returns:
            Position P&L data or None
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqPnLSingle(req_id, account, model_code, con_id)
            response = self._wait_for_response(queue, timeout=10)
            if isinstance(response, PnLSingleData):
                response.account = account
                response.con_id = con_id
                response.model_code = model_code
                return response
            return None
        finally:
            self.cancelPnLSingle(req_id)
            self._cleanup_response_queue(req_id)

    def get_scanner_parameters(self) -> str:
        """Get scanner parameters XML.

        Returns:
            Scanner parameters XML string
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqScannerParameters()
            result = self._wait_for_response(queue, timeout=30)
            return str(result)
        finally:
            self._cleanup_response_queue(req_id)

    def get_news_providers(self) -> list[Any]:
        """Get news providers.

        Returns:
            List of news provider info
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqNewsProviders()
            result = self._wait_for_response(queue, timeout=10)
            return list(result) if result else []
        finally:
            self._cleanup_response_queue(req_id)

    def get_historical_news(
        self,
        con_id: int,
        provider_codes: str,
        start_date_time: str,
        end_date_time: str,
        total_results: int = 10,
    ) -> list[NewsHeadline]:
        """Get historical news headlines.

        Args:
            con_id: Contract ID
            provider_codes: Comma-separated provider codes
            start_date_time: Start date/time
            end_date_time: End date/time
            total_results: Max results

        Returns:
            List of news headlines
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqHistoricalNews(
                req_id, con_id, provider_codes, start_date_time, end_date_time, total_results, []
            )
            responses = self._wait_for_response(queue, collect_all=True)
            return [r for r in responses if isinstance(r, NewsHeadline)]
        finally:
            self._cleanup_response_queue(req_id)

    def get_news_article(self, provider_code: str, article_id: str) -> dict[str, Any] | None:
        """Get news article content.

        Args:
            provider_code: News provider code
            article_id: Article ID

        Returns:
            Article content or None
        """
        req_id = self._get_next_req_id()
        queue = self._create_response_queue(req_id)

        try:
            self.reqNewsArticle(req_id, provider_code, article_id, [])
            response = self._wait_for_response(queue, timeout=10)
            if isinstance(response, dict):
                return response
            return None
        finally:
            self._cleanup_response_queue(req_id)
