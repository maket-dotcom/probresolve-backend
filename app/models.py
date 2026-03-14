import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)  # emoji
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    categories: Mapped[list["Category"]] = relationship("Category", back_populates="domain")
    problems: Mapped[list["Problem"]] = relationship("Problem", back_populates="domain")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    domain: Mapped["Domain"] = relationship("Domain", back_populates="categories")
    problems: Mapped[list["Problem"]] = relationship("Problem", back_populates="category")

    __table_args__ = (UniqueConstraint("domain_id", "slug", name="uq_category_domain_slug"),)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    domain_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("domains.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    domain: Mapped["Domain | None"] = relationship("Domain")
    problems: Mapped[list["Problem"]] = relationship("Problem", back_populates="company")

    __table_args__ = (UniqueConstraint("name", "domain_id", name="uq_company_name_domain"),)

class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("domains.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(350), nullable=False)  # decorative, no UNIQUE
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount_lost: Mapped[int | None] = mapped_column(BigInteger)  # in paise / smallest unit
    poster_name: Mapped[str | None] = mapped_column(Text)
    poster_email: Mapped[str | None] = mapped_column(String(255))
    poster_phone: Mapped[str | None] = mapped_column(String(20))
    location_state: Mapped[str | None] = mapped_column(Text)
    date_of_incident: Mapped[date | None] = mapped_column(Date)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    flags_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    upvote_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    domain: Mapped["Domain"] = relationship("Domain", back_populates="problems")
    category: Mapped["Category | None"] = relationship("Category", back_populates="problems")
    company: Mapped["Company | None"] = relationship("Company", back_populates="problems")
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="problem", cascade="all, delete-orphan"
    )
    upvotes: Mapped[list["Upvote"]] = relationship(
        "Upvote", back_populates="problem", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="problem", cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship("Problem", back_populates="evidence")


class Upvote(Base):
    __tablename__ = "upvotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship("Problem", back_populates="upvotes")

    __table_args__ = (
        UniqueConstraint("problem_id", "fingerprint", name="uq_upvote_problem_fingerprint"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship("Problem", back_populates="reports")

    __table_args__ = (
        UniqueConstraint("problem_id", "fingerprint", name="uq_report_problem_fingerprint"),
    )
