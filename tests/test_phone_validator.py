"""
Comprehensive unit tests for the Indian phone number validator in ProblemCreate.

Tests cover every branch in the validator:
  +91 prefix stripping, 91 prefix (12-digit) stripping,
  leading 0 (11-digit) stripping, direct 10-digit input,
  and all the rejection cases.
"""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import ProblemCreate


DOMAIN_ID = uuid.uuid4()
LONG_DESC = "A" * 200


def make_payload(phone: str) -> dict:
    return {
        "domain_id": DOMAIN_ID,
        "title": "Test Complaint Title",
        "description": LONG_DESC,
        "poster_name": "Test User",
        "poster_email": "test@example.com",
        "poster_phone": phone,
    }


def make(phone: str) -> ProblemCreate:
    return ProblemCreate(**make_payload(phone))


def assert_invalid(phone: str) -> None:
    with pytest.raises(ValidationError):
        make(phone)


# ── Valid numbers ─────────────────────────────────────────────────────────────


class TestValidPhoneNumbers:
    def test_10_digit_starting_with_9(self):
        p = make("9876543210")
        assert p.poster_phone == "9876543210"

    def test_10_digit_starting_with_8(self):
        p = make("8765432109")
        assert p.poster_phone == "8765432109"

    def test_10_digit_starting_with_7(self):
        p = make("7654321098")
        assert p.poster_phone == "7654321098"

    def test_10_digit_starting_with_6(self):
        p = make("6543210987")
        assert p.poster_phone == "6543210987"

    def test_strip_plus91_prefix(self):
        p = make("+919876543210")
        assert p.poster_phone == "9876543210"

    def test_strip_91_prefix_when_12_digits(self):
        p = make("919876543210")
        assert p.poster_phone == "9876543210"

    def test_strip_leading_zero_when_11_digits(self):
        p = make("09876543210")
        assert p.poster_phone == "9876543210"

    def test_stored_as_10_digits_without_prefix(self):
        p = make("+918765432109")
        assert len(p.poster_phone) == 10
        assert not p.poster_phone.startswith("+")

    def test_whitespace_stripped_before_validation(self):
        p = make("  9876543210  ")
        assert p.poster_phone == "9876543210"


# ── Invalid numbers ───────────────────────────────────────────────────────────


class TestInvalidPhoneNumbers:
    def test_9_digits_rejected(self):
        assert_invalid("987654321")

    def test_11_digits_without_leading_zero_rejected(self):
        # 11 digits but doesn't start with 0 — not stripped, not 10 digits
        assert_invalid("11987654321")

    def test_starts_with_5_rejected(self):
        assert_invalid("5876543210")

    def test_starts_with_4_rejected(self):
        assert_invalid("4876543210")

    def test_starts_with_3_rejected(self):
        assert_invalid("3876543210")

    def test_starts_with_2_rejected(self):
        assert_invalid("2876543210")

    def test_starts_with_1_rejected(self):
        assert_invalid("1876543210")

    def test_starts_with_0_ten_digits_rejected(self):
        # 10 digits starting with 0 — not the 11-digit-with-leading-0 case
        assert_invalid("0876543210")

    def test_alpha_chars_rejected(self):
        assert_invalid("9abc543210")

    def test_empty_string_rejected(self):
        assert_invalid("")

    def test_spaces_only_rejected(self):
        assert_invalid("   ")

    def test_too_long_rejected(self):
        assert_invalid("99876543210123")

    def test_landline_style_rejected(self):
        # Indian landline: 044-XXXXXXXX (starts with 0, but 8 digits after)
        assert_invalid("04412345678")

    def test_plus_only_rejected(self):
        assert_invalid("+91")

    def test_plus91_without_number_rejected(self):
        assert_invalid("+91   ")


# ── Edge cases for prefix stripping ──────────────────────────────────────────


class TestPrefixStripping:
    def test_91_prefix_with_11_digits_not_stripped(self):
        # "91987654321" = 11 chars but not 12 — should be rejected as not 10 digits
        assert_invalid("91987654321")

    def test_91_prefix_with_13_digits_not_stripped(self):
        # "9198765432100" = 13 chars — not the 12-digit case, not stripped → 13 chars → reject
        assert_invalid("9198765432100")

    def test_plus91_then_valid_10_digit_number(self):
        p = make("+916543210987")
        assert p.poster_phone == "6543210987"

    def test_leading_zero_11_digits_valid_second_digit_must_be_6_to_9(self):
        # 0 + 10 digits starting with 9 → valid
        p = make("09876543210")
        assert p.poster_phone == "9876543210"
        # 0 + 10 digits starting with 5 → after stripping → "5876543210" → invalid
        assert_invalid("05876543210")
