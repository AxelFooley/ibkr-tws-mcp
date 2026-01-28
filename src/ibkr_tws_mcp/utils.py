"""Utility functions for IBKR TWS MCP Server."""

from __future__ import annotations

from ibapi.contract import Contract
from ibapi.order import Order

from .models import ContractSpec, OrderAction, OrderSpec, OrderType, SecurityType, TimeInForce


def create_contract(spec: ContractSpec) -> Contract:
    """Create an ibapi Contract from a ContractSpec.

    Args:
        spec: Contract specification

    Returns:
        ibapi Contract object
    """
    contract = Contract()
    contract.symbol = spec.symbol
    if isinstance(spec.sec_type, SecurityType):
        contract.secType = spec.sec_type.value
    else:
        contract.secType = spec.sec_type
    contract.exchange = spec.exchange
    contract.currency = spec.currency

    if spec.con_id:
        contract.conId = spec.con_id
    if spec.last_trade_date_or_contract_month:
        contract.lastTradeDateOrContractMonth = spec.last_trade_date_or_contract_month
    if spec.strike:
        contract.strike = spec.strike
    if spec.right:
        contract.right = spec.right
    if spec.multiplier:
        contract.multiplier = spec.multiplier
    if spec.local_symbol:
        contract.localSymbol = spec.local_symbol
    if spec.primary_exchange:
        contract.primaryExchange = spec.primary_exchange
    if spec.trading_class:
        contract.tradingClass = spec.trading_class

    return contract


def create_order(spec: OrderSpec) -> Order:
    """Create an ibapi Order from an OrderSpec.

    Args:
        spec: Order specification

    Returns:
        ibapi Order object
    """
    order = Order()
    order.action = spec.action.value if isinstance(spec.action, OrderAction) else spec.action
    if isinstance(spec.order_type, OrderType):
        order.orderType = spec.order_type.value
    else:
        order.orderType = spec.order_type
    order.totalQuantity = spec.total_quantity
    order.tif = spec.tif.value if isinstance(spec.tif, TimeInForce) else spec.tif
    order.transmit = spec.transmit
    order.outsideRth = spec.outside_rth

    if spec.limit_price is not None:
        order.lmtPrice = spec.limit_price
    if spec.aux_price is not None:
        order.auxPrice = spec.aux_price
    if spec.oca_group:
        order.ocaGroup = spec.oca_group
    if spec.oca_type:
        order.ocaType = spec.oca_type
    if spec.account:
        order.account = spec.account
    if spec.parent_id:
        order.parentId = spec.parent_id
    if spec.good_till_date:
        order.goodTillDate = spec.good_till_date
    if spec.trail_stop_price is not None:
        order.trailStopPrice = spec.trail_stop_price
    if spec.trailing_percent is not None:
        order.trailingPercent = spec.trailing_percent

    return order


def create_stock_contract(
    symbol: str,
    exchange: str = "SMART",
    currency: str = "USD",
    primary_exchange: str | None = None,
) -> Contract:
    """Create a stock contract.

    Args:
        symbol: Stock symbol
        exchange: Exchange (default: SMART)
        currency: Currency (default: USD)
        primary_exchange: Primary exchange (optional)

    Returns:
        ibapi Contract for a stock
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = exchange
    contract.currency = currency
    if primary_exchange:
        contract.primaryExchange = primary_exchange
    return contract


def create_option_contract(
    symbol: str,
    expiry: str,
    strike: float,
    right: str,
    exchange: str = "SMART",
    currency: str = "USD",
    multiplier: str = "100",
) -> Contract:
    """Create an option contract.

    Args:
        symbol: Underlying symbol
        expiry: Expiry date (YYYYMMDD)
        strike: Strike price
        right: 'C' for call, 'P' for put
        exchange: Exchange (default: SMART)
        currency: Currency (default: USD)
        multiplier: Contract multiplier (default: 100)

    Returns:
        ibapi Contract for an option
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = exchange
    contract.currency = currency
    contract.lastTradeDateOrContractMonth = expiry
    contract.strike = strike
    contract.right = right
    contract.multiplier = multiplier
    return contract


def create_future_contract(
    symbol: str,
    expiry: str,
    exchange: str,
    currency: str = "USD",
    multiplier: str | None = None,
) -> Contract:
    """Create a futures contract.

    Args:
        symbol: Futures symbol
        expiry: Expiry date (YYYYMM or YYYYMMDD)
        exchange: Exchange
        currency: Currency (default: USD)
        multiplier: Contract multiplier (optional)

    Returns:
        ibapi Contract for a future
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "FUT"
    contract.exchange = exchange
    contract.currency = currency
    contract.lastTradeDateOrContractMonth = expiry
    if multiplier:
        contract.multiplier = multiplier
    return contract


def create_forex_contract(
    symbol: str,
    currency: str = "USD",
    exchange: str = "IDEALPRO",
) -> Contract:
    """Create a forex contract.

    Args:
        symbol: Base currency (e.g., EUR)
        currency: Quote currency (e.g., USD)
        exchange: Exchange (default: IDEALPRO)

    Returns:
        ibapi Contract for forex
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "CASH"
    contract.exchange = exchange
    contract.currency = currency
    return contract


def create_crypto_contract(
    symbol: str,
    currency: str = "USD",
    exchange: str = "PAXOS",
) -> Contract:
    """Create a crypto contract.

    Args:
        symbol: Crypto symbol (e.g., BTC)
        currency: Quote currency (default: USD)
        exchange: Exchange (default: PAXOS)

    Returns:
        ibapi Contract for crypto
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "CRYPTO"
    contract.exchange = exchange
    contract.currency = currency
    return contract


def create_market_order(
    action: str,
    quantity: float,
    account: str | None = None,
    outside_rth: bool = False,
) -> Order:
    """Create a market order.

    Args:
        action: 'BUY' or 'SELL'
        quantity: Number of shares/contracts
        account: Account to use (optional)
        outside_rth: Allow trading outside regular hours

    Returns:
        Market order
    """
    order = Order()
    order.action = action
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.outsideRth = outside_rth
    if account:
        order.account = account
    return order


def create_limit_order(
    action: str,
    quantity: float,
    limit_price: float,
    account: str | None = None,
    tif: str = "DAY",
    outside_rth: bool = False,
) -> Order:
    """Create a limit order.

    Args:
        action: 'BUY' or 'SELL'
        quantity: Number of shares/contracts
        limit_price: Limit price
        account: Account to use (optional)
        tif: Time in force (default: DAY)
        outside_rth: Allow trading outside regular hours

    Returns:
        Limit order
    """
    order = Order()
    order.action = action
    order.orderType = "LMT"
    order.totalQuantity = quantity
    order.lmtPrice = limit_price
    order.tif = tif
    order.outsideRth = outside_rth
    if account:
        order.account = account
    return order


def create_stop_order(
    action: str,
    quantity: float,
    stop_price: float,
    account: str | None = None,
    tif: str = "DAY",
) -> Order:
    """Create a stop order.

    Args:
        action: 'BUY' or 'SELL'
        quantity: Number of shares/contracts
        stop_price: Stop trigger price
        account: Account to use (optional)
        tif: Time in force (default: DAY)

    Returns:
        Stop order
    """
    order = Order()
    order.action = action
    order.orderType = "STP"
    order.totalQuantity = quantity
    order.auxPrice = stop_price
    order.tif = tif
    if account:
        order.account = account
    return order


def create_stop_limit_order(
    action: str,
    quantity: float,
    stop_price: float,
    limit_price: float,
    account: str | None = None,
    tif: str = "DAY",
) -> Order:
    """Create a stop-limit order.

    Args:
        action: 'BUY' or 'SELL'
        quantity: Number of shares/contracts
        stop_price: Stop trigger price
        limit_price: Limit price once triggered
        account: Account to use (optional)
        tif: Time in force (default: DAY)

    Returns:
        Stop-limit order
    """
    order = Order()
    order.action = action
    order.orderType = "STP LMT"
    order.totalQuantity = quantity
    order.auxPrice = stop_price
    order.lmtPrice = limit_price
    order.tif = tif
    if account:
        order.account = account
    return order


def create_trailing_stop_order(
    action: str,
    quantity: float,
    trailing_amount: float | None = None,
    trailing_percent: float | None = None,
    account: str | None = None,
    tif: str = "DAY",
) -> Order:
    """Create a trailing stop order.

    Args:
        action: 'BUY' or 'SELL'
        quantity: Number of shares/contracts
        trailing_amount: Trailing amount in price (use this OR trailing_percent)
        trailing_percent: Trailing percentage (use this OR trailing_amount)
        account: Account to use (optional)
        tif: Time in force (default: DAY)

    Returns:
        Trailing stop order
    """
    order = Order()
    order.action = action
    order.orderType = "TRAIL"
    order.totalQuantity = quantity
    order.tif = tif

    if trailing_amount is not None:
        order.auxPrice = trailing_amount
    elif trailing_percent is not None:
        order.trailingPercent = trailing_percent
    else:
        raise ValueError("Either trailing_amount or trailing_percent must be specified")

    if account:
        order.account = account
    return order


def format_duration(days: int = 0, weeks: int = 0, months: int = 0, years: int = 0) -> str:
    """Format duration string for historical data requests.

    Args:
        days: Number of days
        weeks: Number of weeks
        months: Number of months
        years: Number of years

    Returns:
        Duration string (e.g., "1 D", "2 W", "3 M", "1 Y")
    """
    if years > 0:
        return f"{years} Y"
    elif months > 0:
        return f"{months} M"
    elif weeks > 0:
        return f"{weeks} W"
    elif days > 0:
        return f"{days} D"
    else:
        return "1 D"
