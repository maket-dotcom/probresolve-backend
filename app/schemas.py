import uuid
from datetime import date, datetime, timezone, timedelta

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ── Evidence ──────────────────────────────────────────────────────────────────

class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_url: str
    file_name: str
    content_type: str | None


# ── Problem ───────────────────────────────────────────────────────────────────

class ProblemCreate(BaseModel):
    domain_id: uuid.UUID
    category_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    title: str
    description: str
    amount_lost: int | None = None  # exact Rupees (no paise conversion)
    poster_name: str
    poster_email: EmailStr
    poster_phone: str
    location_state: str | None = None
    date_of_incident: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        return v

    @field_validator("description")
    @classmethod
    def description_min_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 150:
            raise ValueError(
                "Please describe in more detail (at least 150 characters). "
                "Include dates, amounts, and what steps you already took."
            )
        return v

    @field_validator("poster_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name is required")
        return v

    @field_validator("poster_phone")
    @classmethod
    def validate_indian_phone(cls, v: str) -> str:
        v = v.strip()
        # Strip +91, 91 (if 12 digits), or leading 0
        if v.startswith("+91"):
            v = v[3:]
        elif v.startswith("91") and len(v) == 12:
            v = v[2:]
        elif v.startswith("0") and len(v) == 11:
            v = v[1:]
        v = v.strip()
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        if v[0] not in "6789":
            raise ValueError("Mobile number must start with 6, 7, 8, or 9")
        return v  # stored as 10 digits

    @field_validator("date_of_incident")
    @classmethod
    def no_future_date(cls, v: date | None) -> date | None:
        if v is None:
            return v
        # Today's date in IST (UTC+5:30)
        today_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()
        if v > today_ist:
            raise ValueError("Date of incident cannot be in the future")
        return v


# ── JSON API schemas (Next.js frontend) ───────────────────────────────────────

class DomainEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    icon: str


class CategoryEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class CompanyEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class EscalationLink(BaseModel):
    name: str
    url: str
    description: str


class ProblemListItemV2(BaseModel):
    """Full list item for the JSON API — used by Next.js home feed and search."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    domain: DomainEmbed
    category: CategoryEmbed | None
    company: CompanyEmbed | None
    is_resolved: bool
    is_verified: bool
    flags_cleared: bool
    upvote_count: int
    report_count: int  # computed, not a DB column
    amount_lost: int | None  # exact Rupees — display as-is with Indian formatting
    poster_name: str | None
    location_state: str | None
    date_of_incident: date | None
    created_at: datetime


class ProblemDetailResponse(BaseModel):
    """Full detail response for the JSON API — used by Next.js problem detail page."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    domain: DomainEmbed
    category: CategoryEmbed | None
    company: CompanyEmbed | None
    description: str
    is_resolved: bool
    is_verified: bool
    flags_cleared: bool
    upvote_count: int
    report_count: int
    amount_lost: int | None
    poster_name: str | None
    location_state: str | None
    date_of_incident: date | None
    created_at: datetime
    evidence: list[EvidenceOut]
    has_email: bool  # true if poster provided email — used for credibility panel (email never exposed)
    already_voted: bool
    already_reported: bool
    escalation_links: list[EscalationLink]
