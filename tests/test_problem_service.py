"""
Tests for problem_service Day 4 changes:
- is_hidden filtering in get, list, search
- get_report_counts helper
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, update, select

from app.models import Domain, Problem, Report
from app.services.problem_service import (
    get_problem,
    get_report_counts,
    list_problems,
    search_problems,
)

FP1 = "1111" * 16
FP2 = "2222" * 16


@pytest_asyncio.fixture
async def domain(db):
    result = await db.execute(select(Domain).limit(1))
    d = result.scalar_one_or_none()
    if d is None:
        pytest.skip("No domains seeded — run `python scripts/seed.py` first")
    return d


@pytest_asyncio.fixture
async def visible_problem(db, domain):
    p = Problem(
        domain_id=domain.id,
        title="Visible Test Problem Day4",
        slug="visible-test-problem-day4",
        description="Y" * 200,
        is_hidden=False,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    yield p
    await db.execute(delete(Report).where(Report.problem_id == p.id))
    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


@pytest_asyncio.fixture
async def hidden_problem(db, domain):
    p = Problem(
        domain_id=domain.id,
        title="Hidden Test Problem Day4",
        slug="hidden-test-problem-day4",
        description="Z" * 200,
        is_hidden=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    yield p
    await db.execute(delete(Report).where(Report.problem_id == p.id))
    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


class TestIsHiddenFiltering:
    @pytest.mark.asyncio
    async def test_get_problem_visible_returns_problem(self, db, visible_problem):
        result = await get_problem(db, visible_problem.id)
        assert result is not None
        assert result.id == visible_problem.id

    @pytest.mark.asyncio
    async def test_get_problem_hidden_returns_none(self, db, hidden_problem):
        result = await get_problem(db, hidden_problem.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_problems_excludes_hidden(self, db, visible_problem, hidden_problem):
        problems = await list_problems(db)
        ids = [p.id for p in problems]
        assert visible_problem.id in ids
        assert hidden_problem.id not in ids

    @pytest.mark.asyncio
    async def test_search_excludes_hidden(self, db, visible_problem, hidden_problem):
        results = await search_problems(db, "Test Problem Day4")
        ids = [p.id for p in results]
        assert visible_problem.id in ids
        assert hidden_problem.id not in ids


class TestGetReportCounts:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_dict(self, db):
        result = await get_report_counts(db, [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_problem_with_no_reports_not_in_result(self, db, visible_problem):
        result = await get_report_counts(db, [visible_problem.id])
        # Either not in dict or count is 0
        assert result.get(visible_problem.id, 0) == 0

    @pytest.mark.asyncio
    async def test_report_count_is_accurate(self, db, visible_problem):
        r1 = Report(problem_id=visible_problem.id, fingerprint=FP1, reason="fake")
        r2 = Report(problem_id=visible_problem.id, fingerprint=FP2, reason="other")
        db.add(r1)
        db.add(r2)
        await db.commit()

        result = await get_report_counts(db, [visible_problem.id])
        assert result[visible_problem.id] == 2

        # Cleanup
        await db.execute(delete(Report).where(Report.problem_id == visible_problem.id))
        await db.commit()

    @pytest.mark.asyncio
    async def test_unknown_ids_not_in_result(self, db):
        fake_id = uuid.uuid4()
        result = await get_report_counts(db, [fake_id])
        assert fake_id not in result
