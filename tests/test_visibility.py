"""
Tests for post visibility via HTTP API endpoints.

Covers:
- A post with 5 reports (but NOT hidden) must still be visible on detail + search
- A post with is_hidden=True must return 404 on detail and be absent from search
- Distinction: 5 reports = warning badge only, does NOT auto-hide
"""

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models import Domain, Problem, Report


FP1 = "aaa1" * 16
FP2 = "aaa2" * 16
FP3 = "aaa3" * 16
FP4 = "aaa4" * 16
FP5 = "aaa5" * 16


@pytest_asyncio.fixture
async def domain(db):
    result = await db.execute(select(Domain).limit(1))
    d = result.scalar_one_or_none()
    if d is None:
        pytest.skip("No domains seeded — run `python scripts/seed.py` first")
    return d


@pytest_asyncio.fixture
async def reported_problem(db, domain):
    """A visible (not hidden) post with 5 distinct reports — the 'under review' state."""
    p = Problem(
        domain_id=domain.id,
        title="Visibility Test Reported Problem",
        slug="visibility-test-reported-problem",
        description="X" * 200,
        is_hidden=False,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)

    for fp in [FP1, FP2, FP3, FP4, FP5]:
        db.add(Report(problem_id=p.id, fingerprint=fp, reason="fake"))
    await db.commit()

    yield p

    await db.execute(delete(Report).where(Report.problem_id == p.id))
    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


@pytest_asyncio.fixture
async def hidden_problem(db, domain):
    """A post that has been explicitly hidden by admin (is_hidden=True)."""
    p = Problem(
        domain_id=domain.id,
        title="Visibility Test Hidden Problem",
        slug="visibility-test-hidden-problem",
        description="Y" * 200,
        is_hidden=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)

    yield p

    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


class TestReportedButNotHidden:
    """5 reports = under review badge in admin. Must NOT affect public visibility."""

    @pytest.mark.asyncio
    async def test_detail_page_returns_200(self, client, reported_problem):
        resp = await client.get(f"/api/problems/{reported_problem.id}")
        assert resp.status_code == 200, (
            f"Expected 200 but got {resp.status_code}. "
            "A post with 5 reports but is_hidden=False must still be publicly visible."
        )

    @pytest.mark.asyncio
    async def test_detail_page_returns_correct_report_count(self, client, reported_problem):
        resp = await client.get(f"/api/problems/{reported_problem.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_count"] == 5, (
            f"Expected report_count=5, got {data['report_count']}"
        )

    @pytest.mark.asyncio
    async def test_reported_problem_appears_in_search(self, client, reported_problem):
        resp = await client.get("/api/search?q=Visibility+Test+Reported+Problem")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(reported_problem.id) in ids, (
            "Post with 5 reports but is_hidden=False must appear in search results."
        )

    @pytest.mark.asyncio
    async def test_reported_problem_appears_in_home_feed(self, client, reported_problem):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(reported_problem.id) in ids, (
            "Post with 5 reports but is_hidden=False must appear in the home feed."
        )


class TestHiddenByAdmin:
    """is_hidden=True = admin explicitly hid it. Must be invisible everywhere on public frontend."""

    @pytest.mark.asyncio
    async def test_detail_page_returns_404(self, client, hidden_problem):
        resp = await client.get(f"/api/problems/{hidden_problem.id}")
        assert resp.status_code == 404, (
            f"Expected 404 for hidden post but got {resp.status_code}."
        )

    @pytest.mark.asyncio
    async def test_hidden_problem_absent_from_search(self, client, hidden_problem):
        resp = await client.get("/api/search?q=Visibility+Test+Hidden+Problem")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(hidden_problem.id) not in ids, (
            "Hidden post must NOT appear in search results."
        )

    @pytest.mark.asyncio
    async def test_hidden_problem_absent_from_home_feed(self, client, hidden_problem):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(hidden_problem.id) not in ids, (
            "Hidden post must NOT appear in the home feed."
        )
