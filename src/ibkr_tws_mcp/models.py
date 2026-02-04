"""Pydantic models for IBKR TWS MCP Server."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecurityType(str, Enum):
    """Security types supported by TWS."""

    STOCK = "STK"
    OPTION = "OPT"
    FUTURE = "FUT"
    INDEX = "IND"
    FUTURES_OPTION = "FOP"
    CASH = "CASH"
    CFD = "CFD"
    BOND = "BOND"
    WARRANT = "WAR"
    COMMODITY = "CMDTY"
    NEWS = "NEWS"
    FUND = "FUND"
    CRYPTO = "CRYPTO"


class OrderAction(str, Enum):
    """Order action types."""

    BUY = "BUY"
    SELL = "SELL"
    SSHORT = "SSHORT"


class OrderType(str, Enum):
    """Order types supported by TWS."""

    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"
    TRAILING_STOP = "TRAIL"
    TRAILING_STOP_LIMIT = "TRAIL LIMIT"
    MARKET_ON_CLOSE = "MOC"
    LIMIT_ON_CLOSE = "LOC"
    MARKET_ON_OPEN = "MOO"
    LIMIT_ON_OPEN = "LOO"
    MIDPRICE = "MIDPRICE"
    MARKET_IF_TOUCHED = "MIT"
    LIMIT_IF_TOUCHED = "LIT"


class TimeInForce(str, Enum):
    """Time in force options."""

    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTD = "GTD"  # Good Till Date
    OPG = "OPG"  # Market On Open
    DTC = "DTC"  # Day Till Cancelled


class OrderStatus(str, Enum):
    """Order status values."""

    PENDING_SUBMIT = "PendingSubmit"
    PENDING_CANCEL = "PendingCancel"
    PRE_SUBMITTED = "PreSubmitted"
    SUBMITTED = "Submitted"
    CANCELLED = "Cancelled"
    FILLED = "Filled"
    INACTIVE = "Inactive"
    API_PENDING = "ApiPending"
    API_CANCELLED = "ApiCancelled"


class BarSize(str, Enum):
    """Bar size settings for historical data."""

    SEC_1 = "1 secs"
    SEC_5 = "5 secs"
    SEC_10 = "10 secs"
    SEC_15 = "15 secs"
    SEC_30 = "30 secs"
    MIN_1 = "1 min"
    MIN_2 = "2 mins"
    MIN_3 = "3 mins"
    MIN_5 = "5 mins"
    MIN_10 = "10 mins"
    MIN_15 = "15 mins"
    MIN_20 = "20 mins"
    MIN_30 = "30 mins"
    HOUR_1 = "1 hour"
    HOUR_2 = "2 hours"
    HOUR_3 = "3 hours"
    HOUR_4 = "4 hours"
    HOUR_8 = "8 hours"
    DAY_1 = "1 day"
    WEEK_1 = "1 week"
    MONTH_1 = "1 month"


class WhatToShow(str, Enum):
    """What to show for historical data requests."""

    TRADES = "TRADES"
    MIDPOINT = "MIDPOINT"
    BID = "BID"
    ASK = "ASK"
    BID_ASK = "BID_ASK"
    ADJUSTED_LAST = "ADJUSTED_LAST"
    HISTORICAL_VOLATILITY = "HISTORICAL_VOLATILITY"
    OPTION_IMPLIED_VOLATILITY = "OPTION_IMPLIED_VOLATILITY"
    REBATE_RATE = "REBATE_RATE"
    FEE_RATE = "FEE_RATE"
    YIELD_BID = "YIELD_BID"
    YIELD_ASK = "YIELD_ASK"
    YIELD_BID_ASK = "YIELD_BID_ASK"
    YIELD_LAST = "YIELD_LAST"
    SCHEDULE = "SCHEDULE"


class ContractSpec(BaseModel):
    """Contract specification for identifying securities."""

    symbol: str = Field(..., description="The symbol of the security")
    sec_type: SecurityType = Field(
        default=SecurityType.STOCK, description="Security type (STK, OPT, FUT, etc.)"
    )
    exchange: str = Field(default="SMART", description="Exchange to route orders to")
    currency: str = Field(default="USD", description="Currency of the security")
    con_id: int | None = Field(default=None, description="Contract ID (unique identifier)")
    last_trade_date_or_contract_month: str | None = Field(
        default=None, description="Expiry date for options/futures (YYYYMMDD or YYYYMM)"
    )
    strike: float | None = Field(default=None, description="Strike price for options")
    right: str | None = Field(default=None, description="Option right: 'C' for call, 'P' for put")
    multiplier: str | None = Field(default=None, description="Contract multiplier")
    local_symbol: str | None = Field(default=None, description="Local exchange symbol")
    primary_exchange: str | None = Field(
        default=None, description="Primary exchange for the security"
    )
    trading_class: str | None = Field(default=None, description="Trading class")


class OrderSpec(BaseModel):
    """Order specification for placing orders."""

    action: OrderAction = Field(..., description="Order action: BUY, SELL, or SSHORT")
    order_type: OrderType = Field(..., description="Order type: MKT, LMT, STP, etc.")
    total_quantity: float = Field(..., description="Total quantity to trade", gt=0)
    limit_price: float | None = Field(default=None, description="Limit price for limit orders")
    aux_price: float | None = Field(
        default=None, description="Auxiliary price (stop price for stop orders)"
    )
    tif: TimeInForce = Field(default=TimeInForce.DAY, description="Time in force")
    oca_group: str | None = Field(default=None, description="OCA group name")
    oca_type: int | None = Field(default=None, description="OCA type (1, 2, or 3)")
    account: str | None = Field(default=None, description="Account to use for the order")
    transmit: bool = Field(default=True, description="Whether to transmit the order immediately")
    parent_id: int | None = Field(default=None, description="Parent order ID for bracket orders")
    outside_rth: bool = Field(default=False, description="Allow trading outside regular hours")
    good_till_date: str | None = Field(
        default=None, description="Expiry date for GTD orders (YYYYMMDD HH:MM:SS)"
    )
    trail_stop_price: float | None = Field(
        default=None, description="Trail stop price for trailing stop orders"
    )
    trailing_percent: float | None = Field(
        default=None, description="Trailing percent for trailing stop orders"
    )


class PositionInfo(BaseModel):
    """Position information."""

    account: str = Field(..., description="Account holding the position")
    symbol: str = Field(..., description="Symbol of the security")
    sec_type: str = Field(..., description="Security type")
    exchange: str = Field(..., description="Exchange")
    currency: str = Field(..., description="Currency")
    position: float = Field(..., description="Position quantity (negative for short)")
    avg_cost: float = Field(..., description="Average cost per share")
    con_id: int | None = Field(default=None, description="Contract ID")
    market_value: float | None = Field(default=None, description="Current market value")
    unrealized_pnl: float | None = Field(default=None, description="Unrealized P&L")
    realized_pnl: float | None = Field(default=None, description="Realized P&L")


class AccountSummaryItem(BaseModel):
    """Single account summary item."""

    tag: str = Field(..., description="Tag name (e.g., NetLiquidation, TotalCashValue)")
    value: str = Field(..., description="Value of the tag")
    currency: str = Field(..., description="Currency of the value")


class AccountSummary(BaseModel):
    """Account summary information."""

    account: str = Field(..., description="Account ID")
    items: list[AccountSummaryItem] = Field(default_factory=list, description="Summary items")


class AccountValueItem(BaseModel):
    """Single account value item from reqAccountUpdates."""

    key: str = Field(..., description="Value key (e.g., NetLiquidation, TotalCashValue)")
    value: str = Field(..., description="Value")
    currency: str = Field(..., description="Currency of the value")


class AccountUpdate(BaseModel):
    """Account update information from reqAccountUpdates.

    This is the preferred way to get account data for single accounts
    or unified accounts. For Financial Advisor multi-account setups,
    use AccountSummary instead.
    """

    account: str = Field(..., description="Account ID")
    values: list[AccountValueItem] = Field(
        default_factory=list, description="Account value items"
    )


class ExecutionInfo(BaseModel):
    """Execution report information."""

    exec_id: str = Field(..., description="Execution ID")
    order_id: int = Field(..., description="Order ID")
    account: str = Field(..., description="Account")
    symbol: str = Field(..., description="Symbol")
    sec_type: str = Field(..., description="Security type")
    exchange: str = Field(..., description="Exchange")
    side: str = Field(..., description="Side (BOT or SLD)")
    shares: float = Field(..., description="Number of shares executed")
    price: float = Field(..., description="Execution price")
    perm_id: int = Field(..., description="Permanent ID")
    client_id: int = Field(..., description="Client ID")
    liquidation: int = Field(default=0, description="Liquidation flag")
    cum_qty: float = Field(default=0, description="Cumulative quantity")
    avg_price: float = Field(default=0, description="Average price")
    order_ref: str = Field(default="", description="Order reference")
    ev_rule: str = Field(default="", description="EV rule")
    ev_multiplier: float = Field(default=0, description="EV multiplier")
    model_code: str = Field(default="", description="Model code")
    last_liquidity: int = Field(default=0, description="Last liquidity")
    time: str = Field(default="", description="Execution time")


class BarData(BaseModel):
    """Historical or real-time bar data."""

    date: str = Field(..., description="Bar date/time")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: int = Field(..., description="Volume")
    wap: float = Field(default=0.0, description="Weighted average price")
    bar_count: int = Field(default=0, description="Number of trades in bar")


class TickData(BaseModel):
    """Market data tick."""

    ticker_id: int = Field(..., description="Ticker ID")
    field: str = Field(..., description="Field name (e.g., bid, ask, last)")
    price: float | None = Field(default=None, description="Price value")
    size: int | None = Field(default=None, description="Size value")
    attribs: dict[str, Any] = Field(default_factory=dict, description="Tick attributes")


class OrderState(BaseModel):
    """Order state information."""

    order_id: int = Field(..., description="Order ID")
    status: OrderStatus = Field(..., description="Order status")
    filled: float = Field(default=0, description="Filled quantity")
    remaining: float = Field(default=0, description="Remaining quantity")
    avg_fill_price: float = Field(default=0, description="Average fill price")
    last_fill_price: float = Field(default=0, description="Last fill price")
    perm_id: int = Field(default=0, description="Permanent ID")
    parent_id: int = Field(default=0, description="Parent order ID")
    client_id: int = Field(default=0, description="Client ID")
    why_held: str = Field(default="", description="Why order is held")
    mkt_cap_price: float = Field(default=0, description="Market cap price")


class OpenOrder(BaseModel):
    """Open order information."""

    order_id: int = Field(..., description="Order ID")
    contract: ContractSpec = Field(..., description="Contract specification")
    order: OrderSpec = Field(..., description="Order specification")
    order_state: OrderState = Field(..., description="Order state")


class ContractDetails(BaseModel):
    """Contract details information."""

    contract: ContractSpec = Field(..., description="Contract specification")
    market_name: str = Field(default="", description="Market name")
    min_tick: float = Field(default=0.01, description="Minimum price increment")
    price_magnifier: int = Field(default=1, description="Price magnifier")
    order_types: str = Field(default="", description="Supported order types")
    valid_exchanges: str = Field(default="", description="Valid exchanges")
    under_con_id: int = Field(default=0, description="Underlying contract ID")
    long_name: str = Field(default="", description="Long name")
    contract_month: str = Field(default="", description="Contract month")
    industry: str = Field(default="", description="Industry classification")
    category: str = Field(default="", description="Category")
    subcategory: str = Field(default="", description="Subcategory")
    time_zone_id: str = Field(default="", description="Time zone ID")
    trading_hours: str = Field(default="", description="Trading hours")
    liquid_hours: str = Field(default="", description="Liquid hours")
    ev_rule: str = Field(default="", description="EV rule")
    ev_multiplier: float = Field(default=0, description="EV multiplier")


class PnLData(BaseModel):
    """Profit and Loss data."""

    account: str = Field(..., description="Account")
    daily_pnl: float = Field(default=0, description="Daily P&L")
    unrealized_pnl: float = Field(default=0, description="Unrealized P&L")
    realized_pnl: float = Field(default=0, description="Realized P&L")
    model_code: str = Field(default="", description="Model code")


class PnLSingleData(BaseModel):
    """Position-level P&L data."""

    account: str = Field(..., description="Account")
    con_id: int = Field(..., description="Contract ID")
    position: float = Field(default=0, description="Position size")
    daily_pnl: float = Field(default=0, description="Daily P&L")
    unrealized_pnl: float = Field(default=0, description="Unrealized P&L")
    realized_pnl: float = Field(default=0, description="Realized P&L")
    value: float = Field(default=0, description="Position value")
    model_code: str = Field(default="", description="Model code")


class NewsHeadline(BaseModel):
    """News headline data."""

    time: str = Field(..., description="Time of the headline")
    provider_code: str = Field(..., description="News provider code")
    article_id: str = Field(..., description="Article ID")
    headline: str = Field(..., description="Headline text")
    extra_data: str = Field(default="", description="Extra data")


class ScannerResult(BaseModel):
    """Market scanner result."""

    rank: int = Field(..., description="Rank in scan results")
    contract: ContractSpec = Field(..., description="Contract")
    distance: str = Field(default="", description="Distance from benchmark")
    benchmark: str = Field(default="", description="Benchmark value")
    projection: str = Field(default="", description="Projection")
    legs_str: str = Field(default="", description="Legs string for combos")


class CommissionReport(BaseModel):
    """Commission report data."""

    exec_id: str = Field(..., description="Execution ID")
    commission: float = Field(..., description="Commission amount")
    currency: str = Field(..., description="Currency")
    realized_pnl: float = Field(default=0, description="Realized P&L")
    yield_value: float = Field(default=0, description="Yield")
    yield_redemption_date: str = Field(default="", description="Yield redemption date")
