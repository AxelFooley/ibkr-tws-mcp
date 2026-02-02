"""Utility functions for IBKR TWS MCP Server."""

from __future__ import annotations

import re
from datetime import datetime

from ibapi.contract import Contract
from ibapi.order import Order

from .models import ContractSpec, OrderAction, OrderSpec, OrderType, SecurityType, TimeInForce

# ==================== Input Validation ====================

# Symbol pattern: 1-20 alphanumeric characters, dots, underscores, and slashes
# Supports: AAPL, BRK.B, BTC/USD, EUR/USD, ES_202503
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9._/]{1,20}$")

# Currency pattern: 3 uppercase letters (ISO 4217)
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")

# Exchange pattern: alphanumeric, can include dots (e.g., ISLAND, SMART, NYSE.ARCA)
EXCHANGE_PATTERN = re.compile(r"^[A-Za-z0-9.]{1,20}$")

# Date pattern for expiry: YYYYMMDD or YYYYMM
DATE_PATTERN = re.compile(r"^(\d{6}|\d{8})$")

# DateTime pattern: YYYYMMDD HH:MM:SS
DATETIME_PATTERN = re.compile(r"^\d{8} \d{2}:\d{2}:\d{2}$")


class ValidationError(ValueError):
    """Exception raised for input validation errors."""

    pass


def validate_symbol(symbol: str) -> str:
    """Validate and normalize a trading symbol.

    Args:
        symbol: Symbol to validate (e.g., "AAPL", "BRK.B", "EUR/USD")

    Returns:
        Uppercase normalized symbol

    Raises:
        ValidationError: If symbol format is invalid
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty")
    if not SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Symbols must be 1-20 alphanumeric characters, dots, underscores, or slashes."
        )
    return symbol.upper()


def validate_currency(currency: str) -> str:
    """Validate a currency code.

    Args:
        currency: ISO 4217 currency code (e.g., "USD", "EUR")

    Returns:
        Uppercase currency code

    Raises:
        ValidationError: If currency format is invalid
    """
    if not currency:
        raise ValidationError("Currency cannot be empty")
    currency = currency.upper()
    if not CURRENCY_PATTERN.match(currency):
        raise ValidationError(
            f"Invalid currency format: '{currency}'. "
            "Currency must be a 3-letter ISO 4217 code (e.g., USD, EUR)."
        )
    return currency


def validate_exchange(exchange: str) -> str:
    """Validate an exchange code.

    Args:
        exchange: Exchange code (e.g., "SMART", "NYSE", "ISLAND")

    Returns:
        Uppercase exchange code

    Raises:
        ValidationError: If exchange format is invalid
    """
    if not exchange:
        raise ValidationError("Exchange cannot be empty")
    if not EXCHANGE_PATTERN.match(exchange):
        raise ValidationError(
            f"Invalid exchange format: '{exchange}'. Exchange must be 1-20 alphanumeric characters."
        )
    return exchange.upper()


def validate_quantity(quantity: float, min_value: float = 0.0001) -> float:
    """Validate a quantity value.

    Args:
        quantity: Quantity to validate
        min_value: Minimum allowed value (default: 0.0001 for fractional shares)

    Returns:
        Validated quantity

    Raises:
        ValidationError: If quantity is invalid
    """
    if quantity < min_value:
        raise ValidationError(f"Quantity must be at least {min_value}, got: {quantity}")
    if quantity > 1_000_000_000:  # 1 billion max - reasonable upper bound
        raise ValidationError(f"Quantity too large: {quantity}. Maximum is 1,000,000,000.")
    return quantity


def validate_price(price: float, allow_zero: bool = False) -> float:
    """Validate a price value.

    Args:
        price: Price to validate
        allow_zero: Whether to allow zero price (for market orders)

    Returns:
        Validated price

    Raises:
        ValidationError: If price is invalid
    """
    if price < 0:
        raise ValidationError(f"Price cannot be negative: {price}")
    if not allow_zero and price == 0:
        raise ValidationError("Price cannot be zero")
    if price > 1_000_000_000:  # 1 billion max
        raise ValidationError(f"Price too large: {price}. Maximum is 1,000,000,000.")
    return price


def validate_expiry_date(expiry: str | None) -> str | None:
    """Validate an expiry date string.

    Args:
        expiry: Expiry date in YYYYMMDD or YYYYMM format

    Returns:
        Validated expiry string or None

    Raises:
        ValidationError: If date format is invalid
    """
    if not expiry:
        return None

    if not DATE_PATTERN.match(expiry):
        raise ValidationError(
            f"Invalid expiry date format: '{expiry}'. Expected YYYYMMDD or YYYYMM format."
        )

    # Validate it's a real date
    try:
        if len(expiry) == 8:
            datetime.strptime(expiry, "%Y%m%d")
        else:
            datetime.strptime(expiry + "01", "%Y%m%d")
    except ValueError as e:
        raise ValidationError(f"Invalid date: '{expiry}'. {e}") from e

    return expiry


def validate_datetime(dt_str: str | None) -> str | None:
    """Validate a datetime string.

    Args:
        dt_str: Datetime in "YYYYMMDD HH:MM:SS" format or empty string

    Returns:
        Validated datetime string or None

    Raises:
        ValidationError: If datetime format is invalid
    """
    if not dt_str:
        return dt_str  # Empty string is valid (means "now")

    if not DATETIME_PATTERN.match(dt_str):
        raise ValidationError(
            f"Invalid datetime format: '{dt_str}'. Expected 'YYYYMMDD HH:MM:SS' format."
        )

    # Validate it's a real datetime
    try:
        datetime.strptime(dt_str, "%Y%m%d %H:%M:%S")
    except ValueError as e:
        raise ValidationError(f"Invalid datetime: '{dt_str}'. {e}") from e

    return dt_str


def validate_strike(strike: float | None) -> float | None:
    """Validate an option strike price.

    Args:
        strike: Strike price to validate

    Returns:
        Validated strike price or None

    Raises:
        ValidationError: If strike is invalid
    """
    if strike is None:
        return None
    return validate_price(strike, allow_zero=False)


def validate_option_right(right: str | None) -> str | None:
    """Validate an option right (call/put).

    Args:
        right: Option right ("C" or "P")

    Returns:
        Validated uppercase right or None

    Raises:
        ValidationError: If right is invalid
    """
    if not right:
        return None

    right = right.upper()
    if right not in ("C", "P", "CALL", "PUT"):
        raise ValidationError(f"Invalid option right: '{right}'. Expected 'C' or 'P'.")

    # Normalize to single letter
    if right == "CALL":
        return "C"
    if right == "PUT":
        return "P"
    return right


def validate_con_id(con_id: int | None) -> int | None:
    """Validate a contract ID.

    Args:
        con_id: Contract ID to validate

    Returns:
        Validated contract ID or None

    Raises:
        ValidationError: If con_id is invalid
    """
    if con_id is None:
        return None
    if con_id <= 0:
        raise ValidationError(f"Contract ID must be positive: {con_id}")
    return con_id


def validate_order_id(order_id: int) -> int:
    """Validate an order ID.

    Args:
        order_id: Order ID to validate

    Returns:
        Validated order ID

    Raises:
        ValidationError: If order_id is invalid
    """
    if order_id <= 0:
        raise ValidationError(f"Order ID must be positive: {order_id}")
    return order_id


def validate_total_results(total_results: int, max_results: int = 10000) -> int:
    """Validate a total results count.

    Args:
        total_results: Number of results requested
        max_results: Maximum allowed results

    Returns:
        Validated total results

    Raises:
        ValidationError: If total_results is invalid
    """
    if total_results <= 0:
        raise ValidationError(f"Total results must be positive: {total_results}")
    if total_results > max_results:
        raise ValidationError(
            f"Total results too large: {total_results}. Maximum is {max_results}."
        )
    return total_results


# ==================== Contract and Order Creation ====================


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
