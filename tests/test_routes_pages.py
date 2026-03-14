"""
Tests for JSON API routes — replaces the old Jinja2 page route tests.
HTML pages now live in Next.js; FastAPI exposes /api/* JSON endpoints.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update

from app.models import Domain, Problem, Report, Upvote


@pytest_asyncio.fixture
async def live_problem(db):
    result = await db.execute(select(Domain).limit(1))
    domain = result.scalar_one_or_none()
    if domain is None:
        pytest.skip("No domains seeded")

    p = Problem(
        domain_id=domain.id,
        title="Page Route Test Problem",
        slug="page-route-test-problem",
        description="B" * 200,
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
async def hidden_problem(db):
    result = await db.execute(select(Domain).limit(1))
    domain = result.scalar_one_or_none()
    if domain is None:
        pytest.skip("No domains seeded")

    p = Problem(
        domain_id=domain.id,
        title="Hidden Page Test Problem",
        slug="hidden-page-test-problem",
        description="C" * 200,
        is_hidden=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    yield p
    await db.execute(delete(Report).where(Report.problem_id == p.id))
    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


class TestApiProblems:
    @pytest.mark.asyncio
    async def test_list_returns_200(self, client):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_domain_filter_returns_200(self, client, db):
        result = await db.execute(select(Domain).limit(1))
        domain = result.scalar_one_or_none()
        if domain is None:
            pytest.skip("No domains seeded")
        resp = await client.get(f"/api/problems?domain_id={domain.id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_excludes_hidden_problems(self, client, hidden_problem):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert str(hidden_problem.id) not in ids

    @pytest.mark.asyncio
    async def test_list_items_have_required_fields(self, client, live_problem):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) > 0
        item = items[0]
        for field in ("id", "title", "slug", "domain", "upvote_count", "report_count",
                      "is_verified", "flags_cleared", "is_resolved"):
            assert field in item, f"missing field: {field}"


class TestApiProblemDetail:
    @pytest.mark.asyncio
    async def test_visible_problem_returns_200(self, client, live_problem):
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_hidden_problem_returns_404(self, client, hidden_problem):
        resp = await client.get(f"/api/problems/{hidden_problem.id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_nonexistent_problem_returns_404(self, client):
        import uuid
        resp = await client.get(f"/api/problems/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_detail_has_all_fields(self, client, live_problem):
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("id", "title", "description", "domain", "evidence",
                      "already_voted", "already_reported", "report_count",
                      "escalation_links", "is_verified", "flags_cleared"):
            assert field in data, f"missing field: {field}"

    @pytest.mark.asyncio
    async def test_detail_has_escalation_links(self, client, live_problem):
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["escalation_links"], list)
        assert len(data["escalation_links"]) > 0

    @pytest.mark.asyncio
    async def test_verified_problem_has_is_verified_true(self, client, db, live_problem):
        from sqlalchemy import update
        from app.models import Problem
        await db.execute(
            update(Problem).where(Problem.id == live_problem.id).values(is_verified=True)
        )
        await db.commit()

        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

        await db.execute(
            update(Problem).where(Problem.id == live_problem.id).values(is_verified=False)
        )
        await db.commit()

    @pytest.mark.asyncio
    async def test_report_count_reflects_reports(self, client, db, live_problem):
        fingerprints = [f"{i:04d}" * 16 for i in range(1, 6)]
        for fp in fingerprints:
            db.add(Report(problem_id=live_problem.id, fingerprint=fp, reason="fake"))
        await db.commit()

        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        assert resp.json()["report_count"] >= 5

        await db.execute(delete(Report).where(Report.problem_id == live_problem.id))
        await db.commit()

    @pytest.mark.asyncio
    async def test_flags_cleared_in_response(self, client, db, live_problem):
        from sqlalchemy import update
        from app.models import Problem
        await db.execute(
            update(Problem).where(Problem.id == live_problem.id).values(flags_cleared=True)
        )
        await db.commit()

        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        assert resp.json()["flags_cleared"] is True

        await db.execute(
            update(Problem).where(Problem.id == live_problem.id).values(flags_cleared=False)
        )
        await db.commit()


    @pytest.mark.asyncio
    async def test_detail_has_email_false_when_no_email(self, client, live_problem):
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        assert resp.json()["has_email"] is False

    @pytest.mark.asyncio
    async def test_detail_has_email_true_when_email_provided(self, client, db, live_problem):
        await db.execute(
            update(Problem)
            .where(Problem.id == live_problem.id)
            .values(poster_email="test@example.com")
        )
        await db.commit()
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        assert resp.json()["has_email"] is True

    @pytest.mark.asyncio
    async def test_detail_escalation_links_have_correct_structure(self, client, live_problem):
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        links = resp.json()["escalation_links"]
        assert len(links) > 0
        for link in links:
            assert "name" in link
            assert "url" in link
            assert "description" in link
            assert link["url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_detail_amount_in_paise(self, client, db, live_problem):
        # Store 50000 paise directly; API must return paise — frontend divides by 100
        await db.execute(
            update(Problem)
            .where(Problem.id == live_problem.id)
            .values(amount_lost=50000)
        )
        await db.commit()
        resp = await client.get(f"/api/problems/{live_problem.id}")
        assert resp.status_code == 200
        assert resp.json()["amount_lost"] == 50000


class TestApiUpvote:
    @pytest.mark.asyncio
    async def test_upvote_returns_count_and_flag(self, client, live_problem):
        resp = await client.post(f"/api/problems/{live_problem.id}/upvote")
        assert resp.status_code == 200
        data = resp.json()
        assert "upvote_count" in data
        assert "already_voted" in data
        assert isinstance(data["upvote_count"], int)
        assert data["already_voted"] is True  # just voted → True

    @pytest.mark.asyncio
    async def test_upvote_increments_count(self, client, live_problem):
        r = await client.post(f"/api/problems/{live_problem.id}/upvote")
        assert r.status_code == 200
        assert r.json()["upvote_count"] >= 1

    @pytest.mark.asyncio
    async def test_upvote_dedup_same_fingerprint(self, client, live_problem):
        # Both requests from the same test client → same fingerprint → count stays the same
        r1 = await client.post(f"/api/problems/{live_problem.id}/upvote")
        r2 = await client.post(f"/api/problems/{live_problem.id}/upvote")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["upvote_count"] == r2.json()["upvote_count"]
        assert r2.json()["already_voted"] is True

    @pytest.mark.asyncio
    async def test_upvote_nonexistent_problem(self, client):
        # upvote() handles IntegrityError gracefully — acceptable: 200 with count=0 or 404
        resp = await client.post(f"/api/problems/{uuid.uuid4()}/upvote")
        assert resp.status_code in (200, 404, 422)


class TestApiReport:
    @pytest.mark.asyncio
    async def test_report_returns_count_and_flag(self, client, live_problem):
        resp = await client.post(
            f"/api/problems/{live_problem.id}/report",
            data={"reason": "fake"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report_count" in data
        assert "already_reported" in data
        assert data["already_reported"] is True

    @pytest.mark.asyncio
    async def test_report_increments_count(self, client, live_problem):
        resp = await client.post(
            f"/api/problems/{live_problem.id}/report",
            data={"reason": "duplicate"},
        )
        assert resp.status_code == 200
        assert resp.json()["report_count"] >= 1

    @pytest.mark.asyncio
    async def test_report_dedup_same_fingerprint(self, client, live_problem):
        r1 = await client.post(
            f"/api/problems/{live_problem.id}/report", data={"reason": "fake"}
        )
        r2 = await client.post(
            f"/api/problems/{live_problem.id}/report", data={"reason": "fake"}
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["report_count"] == r2.json()["report_count"]

    @pytest.mark.asyncio
    async def test_report_missing_reason_returns_422(self, client, live_problem):
        resp = await client.post(f"/api/problems/{live_problem.id}/report")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_report_any_string_reason_accepted(self, client, live_problem):
        # FastAPI accepts any string for reason — no enum validation
        resp = await client.post(
            f"/api/problems/{live_problem.id}/report", data={"reason": "other"}
        )
        assert resp.status_code == 200


class TestApiPagination:
    @pytest.mark.asyncio
    async def test_list_page_1_accepted(self, client):
        resp = await client.get("/api/problems?page=1")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_page_2_returns_200(self, client):
        resp = await client.get("/api/problems?page=2")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_search_page_param_accepted(self, client):
        resp = await client.get("/api/search?q=test&page=1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_page_0_returns_422(self, client):
        # page has ge=1 constraint — 0 is invalid
        resp = await client.get("/api/problems?page=0")
        assert resp.status_code == 422


class TestApiSearch:
    @pytest.mark.asyncio
    async def test_search_returns_200(self, client):
        resp = await client.get("/api/search?q=fraud")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty_list(self, client):
        resp = await client.get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_finds_visible_problem(self, client, live_problem):
        resp = await client.get("/api/search?q=Page+Route+Test+Problem")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert str(live_problem.id) in ids

    @pytest.mark.asyncio
    async def test_search_excludes_hidden_problem(self, client, hidden_problem):
        resp = await client.get("/api/search?q=Hidden+Page+Test+Problem")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert str(hidden_problem.id) not in ids


class TestApiDomains:
    @pytest.mark.asyncio
    async def test_domains_returns_list(self, client):
        resp = await client.get("/api/domains")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_domains_have_required_fields(self, client):
        resp = await client.get("/api/domains")
        assert resp.status_code == 200
        domains = resp.json()
        if domains:
            for field in ("id", "name", "slug", "icon"):
                assert field in domains[0]

    @pytest.mark.asyncio
    async def test_domain_categories_returns_list(self, client, db):
        result = await db.execute(select(Domain).limit(1))
        domain = result.scalar_one_or_none()
        if domain is None:
            pytest.skip("No domains seeded")
        resp = await client.get(f"/api/domains/{domain.id}/categories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
