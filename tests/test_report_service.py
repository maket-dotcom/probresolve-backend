"""
Tests for report_service — requires real DB.
Creates a real problem, reports it, cleans up after.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models import Domain, Problem, Report
from app.services.report_service import has_reported, report_problem

FINGERPRINT_A = "aaaa" * 16  # 64 hex chars
FINGERPRINT_B = "bbbb" * 16
FINGERPRINT_C = "cccc" * 16
FINGERPRINT_D = "dddd" * 16
FINGERPRINT_E = "eeee" * 16


@pytest_asyncio.fixture
async def test_problem(db):
    """Create a minimal problem for testing; delete it after the test."""
    # Fetch any existing domain
    result = await db.execute(select(Domain).limit(1))
    domain = result.scalar_one_or_none()
    if domain is None:
        pytest.skip("No domains seeded — run `python scripts/seed.py` first")

    problem = Problem(
        domain_id=domain.id,
        title="Test Report Service Problem",
        slug="test-report-service-problem",
        description="X" * 200,  # meets 150-char minimum
    )
    db.add(problem)
    await db.commit()
    await db.refresh(problem)

    yield problem

    # Cleanup
    await db.execute(delete(Report).where(Report.problem_id == problem.id))
    await db.execute(delete(Problem).where(Problem.id == problem.id))
    await db.commit()


class TestReportService:
    @pytest.mark.asyncio
    async def test_first_report_returns_count_1_and_is_new_true(self, db, test_problem):
        count, is_new = await report_problem(db, test_problem.id, FINGERPRINT_A, "fake")
        assert count == 1
        assert is_new is True

    @pytest.mark.asyncio
    async def test_duplicate_report_returns_is_new_false(self, db, test_problem):
        await report_problem(db, test_problem.id, FINGERPRINT_B, "fake")
        count, is_new = await report_problem(db, test_problem.id, FINGERPRINT_B, "fake")
        assert is_new is False

    @pytest.mark.asyncio
    async def test_duplicate_does_not_increment_count(self, db, test_problem):
        await report_problem(db, test_problem.id, FINGERPRINT_C, "other")
        count1, _ = await report_problem(db, test_problem.id, FINGERPRINT_C, "other")
        count2, _ = await report_problem(db, test_problem.id, FINGERPRINT_C, "other")
        assert count1 == count2

    @pytest.mark.asyncio
    async def test_different_fingerprints_increment_count(self, db, test_problem):
        fingerprints = [FINGERPRINT_A, FINGERPRINT_B, FINGERPRINT_C, FINGERPRINT_D, FINGERPRINT_E]
        for i, fp in enumerate(fingerprints):
            count, is_new = await report_problem(db, test_problem.id, fp, "defamatory")
            assert is_new is True
            assert count == i + 1

    @pytest.mark.asyncio
    async def test_has_reported_false_before_reporting(self, db, test_problem):
        fresh_fp = "ffff" * 16
        result = await has_reported(db, test_problem.id, fresh_fp)
        assert result is False

    @pytest.mark.asyncio
    async def test_has_reported_true_after_reporting(self, db, test_problem):
        fp = "1234" * 16
        await report_problem(db, test_problem.id, fp, "duplicate")
        result = await has_reported(db, test_problem.id, fp)
        assert result is True
