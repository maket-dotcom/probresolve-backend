"""
Tests for schema validation — no DB required.
"""

import datetime
import uuid

import pytest
from pydantic import ValidationError

from app.schemas import DomainEmbed, ProblemCreate, ProblemDetailResponse, ProblemListItemV2


VALID_DOMAIN_ID = uuid.uuid4()
SHORT_DESCRIPTION = "Amazon is fraud"  # 15 chars — must fail
LONG_DESCRIPTION = (
    "On 15 January 2026 I ordered a Samsung TV (order #123-4567890) from Amazon India "
    "for ₹45,000. The seller sent a completely different product — an empty box with "
    "rocks inside. I raised a return request, uploaded photos, and waited 3 weeks. "
    "Amazon customer care kept saying 'under review'. No refund has been issued."
)  # >150 chars — must pass


def base_payload(**kwargs):
    return {
        "domain_id": VALID_DOMAIN_ID,
        "title": "Test Complaint",
        "description": LONG_DESCRIPTION,
        "poster_name": "Test User",
        "poster_email": "test@example.com",
        "poster_phone": "9876543210",
        **kwargs,
    }


class TestDescriptionValidation:
    def test_description_shorter_than_150_is_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ProblemCreate(**base_payload(description=SHORT_DESCRIPTION))
        errors = exc_info.value.errors()
        assert any("150" in str(e["msg"]) for e in errors)

    def test_description_at_exactly_150_chars_is_accepted(self):
        description = "A" * 150
        p = ProblemCreate(**base_payload(description=description))
        assert len(p.description) == 150

    def test_description_above_150_is_accepted(self):
        p = ProblemCreate(**base_payload(description=LONG_DESCRIPTION))
        assert len(p.description) >= 150

    def test_description_stripped_before_length_check(self):
        """Whitespace-padded short description should still fail."""
        padded = "  " + SHORT_DESCRIPTION + "  "
        with pytest.raises(ValidationError):
            ProblemCreate(**base_payload(description=padded))

    def test_empty_description_is_rejected(self):
        with pytest.raises(ValidationError):
            ProblemCreate(**base_payload(description=""))

    def test_whitespace_only_description_is_rejected(self):
        with pytest.raises(ValidationError):
            ProblemCreate(**base_payload(description="   " * 50))

    def test_empty_title_is_rejected(self):
        with pytest.raises(ValidationError):
            ProblemCreate(**base_payload(title="", description=LONG_DESCRIPTION))

    def test_valid_payload_accepted(self):
        p = ProblemCreate(**base_payload())
        assert p.title == "Test Complaint"
        assert p.domain_id == VALID_DOMAIN_ID


_NOW = datetime.datetime.now(datetime.timezone.utc)

_DOMAIN_DICT = {
    "id": uuid.uuid4(),
    "name": "E-commerce",
    "slug": "e-commerce-online-shopping",
    "icon": "🛒",
}


class TestNewSchemas:
    def test_problem_list_item_v2_validates_required_fields(self):
        data = {
            "id": uuid.uuid4(),
            "title": "Fraudulent seller on Flipkart",
            "slug": "fraudulent-seller-on-flipkart",
            "domain": _DOMAIN_DICT,
            "category": None,
            "company": None,
            "is_resolved": False,
            "is_verified": True,
            "flags_cleared": False,
            "upvote_count": 12,
            "report_count": 3,
            "amount_lost": 50000,  # paise
            "poster_name": "Rahul",
            "location_state": "Karnataka",
            "date_of_incident": None,
            "created_at": _NOW,
        }
        item = ProblemListItemV2.model_validate(data)
        assert item.report_count == 3
        assert item.is_verified is True
        assert item.flags_cleared is False
        assert item.amount_lost == 50000
        assert str(item.domain.slug) == "e-commerce-online-shopping"

    def test_problem_detail_response_has_email_logic(self):
        base = {
            "id": uuid.uuid4(),
            "title": "Test",
            "slug": "test",
            "domain": _DOMAIN_DICT,
            "category": None,
            "company": None,
            "description": "A" * 200,
            "is_resolved": False,
            "is_verified": False,
            "flags_cleared": False,
            "upvote_count": 0,
            "report_count": 0,
            "amount_lost": None,
            "poster_name": None,
            "location_state": None,
            "date_of_incident": None,
            "created_at": _NOW,
            "evidence": [],
            "already_voted": False,
            "already_reported": False,
            "escalation_links": [],
        }
        detail_no_email = ProblemDetailResponse.model_validate({**base, "has_email": False})
        assert detail_no_email.has_email is False

        detail_with_email = ProblemDetailResponse.model_validate({**base, "has_email": True})
        assert detail_with_email.has_email is True
