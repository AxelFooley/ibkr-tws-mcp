"""Tests for utility functions and validation."""

from __future__ import annotations

import pytest

from ibkr_tws_mcp.utils import (
    ValidationError,
    validate_con_id,
    validate_currency,
    validate_datetime,
    validate_exchange,
    validate_expiry_date,
    validate_option_right,
    validate_order_id,
    validate_price,
    validate_quantity,
    validate_strike,
    validate_symbol,
    validate_total_results,
)


class TestValidateSymbol:
    """Tests for validate_symbol function."""

    def test_valid_simple_symbol(self) -> None:
        """Test validation of simple stock symbols."""
        assert validate_symbol("AAPL") == "AAPL"
        assert validate_symbol("aapl") == "AAPL"  # Lowercase converted
        assert validate_symbol("MSFT") == "MSFT"

    def test_valid_symbol_with_dots(self) -> None:
        """Test validation of symbols with dots (e.g., BRK.B)."""
        assert validate_symbol("BRK.B") == "BRK.B"
        assert validate_symbol("brk.a") == "BRK.A"

    def test_valid_symbol_with_slash(self) -> None:
        """Test validation of forex pairs (e.g., EUR/USD)."""
        assert validate_symbol("EUR/USD") == "EUR/USD"
        assert validate_symbol("BTC/USD") == "BTC/USD"

    def test_valid_symbol_with_underscore(self) -> None:
        """Test validation of futures symbols."""
        assert validate_symbol("ES_202503") == "ES_202503"

    def test_empty_symbol_raises(self) -> None:
        """Test that empty symbol raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_symbol("")

    def test_invalid_symbol_characters(self) -> None:
        """Test that symbols with invalid characters raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid symbol format"):
            validate_symbol("AAPL!")
        with pytest.raises(ValidationError, match="Invalid symbol format"):
            validate_symbol("AAPL@123")
        with pytest.raises(ValidationError, match="Invalid symbol format"):
            validate_symbol("AAP L")  # Space

    def test_symbol_too_long(self) -> None:
        """Test that symbols over 20 characters raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid symbol format"):
            validate_symbol("A" * 21)


class TestValidateCurrency:
    """Tests for validate_currency function."""

    def test_valid_currencies(self) -> None:
        """Test validation of valid ISO 4217 currency codes."""
        assert validate_currency("USD") == "USD"
        assert validate_currency("usd") == "USD"  # Lowercase converted
        assert validate_currency("EUR") == "EUR"
        assert validate_currency("GBP") == "GBP"
        assert validate_currency("JPY") == "JPY"

    def test_empty_currency_raises(self) -> None:
        """Test that empty currency raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_currency("")

    def test_invalid_currency_length(self) -> None:
        """Test that currencies not exactly 3 characters raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid currency format"):
            validate_currency("US")
        with pytest.raises(ValidationError, match="Invalid currency format"):
            validate_currency("USDD")

    def test_invalid_currency_characters(self) -> None:
        """Test that currencies with non-alpha characters raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid currency format"):
            validate_currency("US1")


class TestValidateExchange:
    """Tests for validate_exchange function."""

    def test_valid_exchanges(self) -> None:
        """Test validation of valid exchange codes."""
        assert validate_exchange("SMART") == "SMART"
        assert validate_exchange("smart") == "SMART"
        assert validate_exchange("NYSE") == "NYSE"
        assert validate_exchange("NASDAQ") == "NASDAQ"
        assert validate_exchange("ISLAND") == "ISLAND"

    def test_valid_exchange_with_dot(self) -> None:
        """Test validation of exchange with dot (e.g., NYSE.ARCA)."""
        assert validate_exchange("NYSE.ARCA") == "NYSE.ARCA"

    def test_empty_exchange_raises(self) -> None:
        """Test that empty exchange raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_exchange("")

    def test_invalid_exchange_characters(self) -> None:
        """Test that exchanges with invalid characters raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid exchange format"):
            validate_exchange("NYSE!")


class TestValidateQuantity:
    """Tests for validate_quantity function."""

    def test_valid_quantities(self) -> None:
        """Test validation of valid quantities."""
        assert validate_quantity(1) == 1
        assert validate_quantity(100) == 100
        assert validate_quantity(0.5) == 0.5  # Fractional shares

    def test_fractional_shares(self) -> None:
        """Test validation of fractional share quantities."""
        assert validate_quantity(0.001) == 0.001
        assert validate_quantity(0.0001) == 0.0001

    def test_quantity_too_small(self) -> None:
        """Test that quantities below minimum raise ValidationError."""
        with pytest.raises(ValidationError, match="must be at least"):
            validate_quantity(0.00001)

    def test_negative_quantity_raises(self) -> None:
        """Test that negative quantities raise ValidationError."""
        with pytest.raises(ValidationError, match="must be at least"):
            validate_quantity(-1)

    def test_quantity_too_large(self) -> None:
        """Test that quantities over 1 billion raise ValidationError."""
        with pytest.raises(ValidationError, match="too large"):
            validate_quantity(2_000_000_000)


class TestValidatePrice:
    """Tests for validate_price function."""

    def test_valid_prices(self) -> None:
        """Test validation of valid prices."""
        assert validate_price(100.50) == 100.50
        assert validate_price(0.01) == 0.01

    def test_zero_price_not_allowed_by_default(self) -> None:
        """Test that zero price raises ValidationError by default."""
        with pytest.raises(ValidationError, match="cannot be zero"):
            validate_price(0)

    def test_zero_price_allowed_when_specified(self) -> None:
        """Test that zero price is allowed when allow_zero=True."""
        assert validate_price(0, allow_zero=True) == 0

    def test_negative_price_raises(self) -> None:
        """Test that negative prices raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be negative"):
            validate_price(-1)

    def test_price_too_large(self) -> None:
        """Test that prices over 1 billion raise ValidationError."""
        with pytest.raises(ValidationError, match="too large"):
            validate_price(2_000_000_000)


class TestValidateExpiryDate:
    """Tests for validate_expiry_date function."""

    def test_valid_yyyymmdd_format(self) -> None:
        """Test validation of YYYYMMDD format dates."""
        assert validate_expiry_date("20250320") == "20250320"
        assert validate_expiry_date("20251215") == "20251215"

    def test_valid_yyyymm_format(self) -> None:
        """Test validation of YYYYMM format dates."""
        assert validate_expiry_date("202503") == "202503"
        assert validate_expiry_date("202512") == "202512"

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert validate_expiry_date(None) is None

    def test_empty_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert validate_expiry_date("") is None

    def test_invalid_format(self) -> None:
        """Test that invalid date formats raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid expiry date format"):
            validate_expiry_date("2025-03-20")  # Wrong format
        with pytest.raises(ValidationError, match="Invalid expiry date format"):
            validate_expiry_date("03/20/2025")

    def test_invalid_date_values(self) -> None:
        """Test that invalid date values raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date"):
            validate_expiry_date("20251320")  # Month 13 doesn't exist


class TestValidateDatetime:
    """Tests for validate_datetime function."""

    def test_valid_datetime(self) -> None:
        """Test validation of valid datetime strings."""
        assert validate_datetime("20250320 14:30:00") == "20250320 14:30:00"
        assert validate_datetime("20251215 09:30:00") == "20251215 09:30:00"

    def test_empty_returns_empty(self) -> None:
        """Test that empty string returns empty (valid for 'now')."""
        assert validate_datetime("") == ""

    def test_none_returns_none(self) -> None:
        """Test that None returns None."""
        assert validate_datetime(None) is None

    def test_invalid_format(self) -> None:
        """Test that invalid datetime formats raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            validate_datetime("2025-03-20 14:30:00")
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            validate_datetime("20250320")  # Missing time


class TestValidateStrike:
    """Tests for validate_strike function."""

    def test_valid_strike(self) -> None:
        """Test validation of valid strike prices."""
        assert validate_strike(150.0) == 150.0
        assert validate_strike(0.50) == 0.50

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert validate_strike(None) is None

    def test_zero_strike_raises(self) -> None:
        """Test that zero strike raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be zero"):
            validate_strike(0)


class TestValidateOptionRight:
    """Tests for validate_option_right function."""

    def test_valid_rights(self) -> None:
        """Test validation of valid option rights."""
        assert validate_option_right("C") == "C"
        assert validate_option_right("P") == "P"
        assert validate_option_right("c") == "C"  # Lowercase converted
        assert validate_option_right("p") == "P"

    def test_full_names(self) -> None:
        """Test that full names are normalized to single letter."""
        assert validate_option_right("CALL") == "C"
        assert validate_option_right("PUT") == "P"
        assert validate_option_right("call") == "C"
        assert validate_option_right("put") == "P"

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert validate_option_right(None) is None

    def test_empty_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert validate_option_right("") is None

    def test_invalid_right_raises(self) -> None:
        """Test that invalid rights raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid option right"):
            validate_option_right("X")


class TestValidateConId:
    """Tests for validate_con_id function."""

    def test_valid_con_id(self) -> None:
        """Test validation of valid contract IDs."""
        assert validate_con_id(265598) == 265598
        assert validate_con_id(1) == 1

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert validate_con_id(None) is None

    def test_zero_raises(self) -> None:
        """Test that zero con_id raises ValidationError."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_con_id(0)

    def test_negative_raises(self) -> None:
        """Test that negative con_id raises ValidationError."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_con_id(-1)


class TestValidateOrderId:
    """Tests for validate_order_id function."""

    def test_valid_order_id(self) -> None:
        """Test validation of valid order IDs."""
        assert validate_order_id(1) == 1
        assert validate_order_id(12345) == 12345

    def test_zero_raises(self) -> None:
        """Test that zero order_id raises ValidationError."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_order_id(0)

    def test_negative_raises(self) -> None:
        """Test that negative order_id raises ValidationError."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_order_id(-1)


class TestValidateTotalResults:
    """Tests for validate_total_results function."""

    def test_valid_total_results(self) -> None:
        """Test validation of valid total results values."""
        assert validate_total_results(10) == 10
        assert validate_total_results(100) == 100
        assert validate_total_results(10000) == 10000

    def test_zero_raises(self) -> None:
        """Test that zero total_results raises ValidationError."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_total_results(0)

    def test_negative_raises(self) -> None:
        """Test that negative total_results raises ValidationError."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_total_results(-1)

    def test_too_large_raises(self) -> None:
        """Test that total_results over max raises ValidationError."""
        with pytest.raises(ValidationError, match="too large"):
            validate_total_results(20000)

    def test_custom_max_results(self) -> None:
        """Test that custom max_results is respected."""
        assert validate_total_results(50, max_results=100) == 50
        with pytest.raises(ValidationError, match="too large"):
            validate_total_results(150, max_results=100)
