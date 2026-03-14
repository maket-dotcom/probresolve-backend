"""
Unit tests for parse_amount_lost() — no DB required.

The function lives in app/routes/problems.py and handles amount input
from the multipart form, including Indian number formatting.
"""

import pytest
from fastapi import HTTPException

from app.routes.problems import parse_amount_lost


class TestParseAmountLost:
    # ── None / empty inputs ───────────────────────────────────────────────────

    def test_none_returns_none(self):
        assert parse_amount_lost(None) is None

    def test_empty_string_returns_none(self):
        assert parse_amount_lost("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_amount_lost("   ") is None

    # ── Plain integers ────────────────────────────────────────────────────────

    def test_plain_integer_string(self):
        assert parse_amount_lost("1000") == 1000

    def test_zero_returns_zero(self):
        assert parse_amount_lost("0") == 0

    def test_large_number(self):
        assert parse_amount_lost("500000") == 500000

    # ── Indian number formatting ──────────────────────────────────────────────

    def test_indian_format_1_lakh(self):
        # "1,00,000" → 100000
        assert parse_amount_lost("1,00,000") == 100000

    def test_indian_format_with_rupee_symbol(self):
        # "₹1,000" → 1000
        assert parse_amount_lost("₹1,000") == 1000

    def test_western_format_1_million(self):
        assert parse_amount_lost("1,000,000") == 1000000

    def test_commas_stripped(self):
        assert parse_amount_lost("10,000") == 10000

    # ── Decimal inputs ────────────────────────────────────────────────────────

    def test_decimal_truncated_at_point(self):
        # "1500.75" → 1500 (truncates at decimal)
        assert parse_amount_lost("1500.75") == 1500

    def test_decimal_only_after_dot_returns_none(self):
        # ".75" → truncates to "" before the dot → None
        assert parse_amount_lost(".75") is None

    def test_zero_before_decimal_returns_zero(self):
        assert parse_amount_lost("0.99") == 0

    # ── Characters and symbols ────────────────────────────────────────────────

    def test_non_digit_chars_stripped(self):
        # "INR5000" — no period, so non-digit prefix stripped → 5000
        assert parse_amount_lost("INR5000") == 5000

    def test_rs_prefix_with_period_truncates_before_digits(self):
        # "Rs. 5,000/-" — the period in "Rs." causes split(".")[0] = "Rs" → no digits → None
        assert parse_amount_lost("Rs. 5,000/-") is None

    def test_spaces_in_number(self):
        assert parse_amount_lost("5 000") == 5000

    def test_all_non_digit_returns_none(self):
        assert parse_amount_lost("abc") is None

    def test_only_special_chars_returns_none(self):
        assert parse_amount_lost("/-") is None

    # ── Boundary / limit ─────────────────────────────────────────────────────

    def test_exactly_1_trillion_is_allowed(self):
        assert parse_amount_lost("1000000000000") == 1_000_000_000_000

    def test_above_1_trillion_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            parse_amount_lost("1000000000001")
        assert exc_info.value.status_code == 422
        assert "maximum" in exc_info.value.detail.lower()

    def test_way_above_limit_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            parse_amount_lost("9" * 15)
        assert exc_info.value.status_code == 422

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_numeric_string_with_leading_whitespace(self):
        assert parse_amount_lost("  5000  ") == 5000

    def test_amount_lost_raw_pure_digits(self):
        # amount_lost_raw from hidden input is always pure digits
        assert parse_amount_lost("100000") == 100000
