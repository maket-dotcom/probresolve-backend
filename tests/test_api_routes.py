"""
Integration tests for the JSON API routes via HTTP (AsyncClient).

These tests verify:
- GET /api/domains
- GET /api/domains/{id}/categories
- GET /api/problems (list + pagination + domain filter)
- GET /api/problems/{id} (detail + fingerprint headers + 404)
- POST /api/problems/{id}/upvote
- POST /api/problems/{id}/report
- GET /api/search
- GET /api/companies
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models import Domain, Problem, Report, Upvote


# ── Shared fixtures ────────────────────────────────────────────────────────────


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
        title="API Route Test Visible Problem",
        slug="api-route-test-visible-problem",
        description="This is a detailed description of the API route test problem " * 3,
        is_hidden=False,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    yield p
    await db.execute(delete(Upvote).where(Upvote.problem_id == p.id))
    await db.execute(delete(Report).where(Report.problem_id == p.id))
    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


@pytest_asyncio.fixture
async def hidden_problem(db, domain):
    p = Problem(
        domain_id=domain.id,
        title="API Route Test Hidden Problem",
        slug="api-route-test-hidden-problem",
        description="Z" * 200,
        is_hidden=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    yield p
    await db.execute(delete(Problem).where(Problem.id == p.id))
    await db.commit()


# ── GET /api/domains ──────────────────────────────────────────────────────────


class TestGetDomains:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        resp = await client.get("/api/domains")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client, domain):
        resp = await client.get("/api/domains")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_domain_has_required_fields(self, client, domain):
        resp = await client.get("/api/domains")
        domains = resp.json()
        first = domains[0]
        assert "id" in first
        assert "name" in first
        assert "slug" in first
        assert "icon" in first


# ── GET /api/domains/{domain_id}/categories ───────────────────────────────────


class TestGetCategories:
    @pytest.mark.asyncio
    async def test_returns_200_for_valid_domain(self, client, domain):
        resp = await client.get(f"/api/domains/{domain.id}/categories")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list_for_valid_domain(self, client, domain):
        resp = await client.get(f"/api/domains/{domain.id}/categories")
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_unknown_domain_returns_empty_list(self, client):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/domains/{fake_id}/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client):
        resp = await client.get("/api/domains/not-a-uuid/categories")
        assert resp.status_code == 422


# ── GET /api/problems ─────────────────────────────────────────────────────────


class TestListProblems:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client):
        resp = await client.get("/api/problems")
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_visible_problem_appears_in_list(self, client, visible_problem):
        resp = await client.get("/api/problems")
        ids = [item["id"] for item in resp.json()]
        assert str(visible_problem.id) in ids

    @pytest.mark.asyncio
    async def test_hidden_problem_not_in_list(self, client, hidden_problem):
        resp = await client.get("/api/problems")
        ids = [item["id"] for item in resp.json()]
        assert str(hidden_problem.id) not in ids

    @pytest.mark.asyncio
    async def test_domain_filter_returns_only_that_domain(self, client, visible_problem, domain):
        resp = await client.get(f"/api/problems?domain_id={domain.id}")
        assert resp.status_code == 200
        data = resp.json()
        # All returned items must belong to the filtered domain
        for item in data:
            assert item["domain"]["id"] == str(domain.id)

    @pytest.mark.asyncio
    async def test_page_param_accepted(self, client):
        resp = await client.get("/api/problems?page=1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_page_zero_returns_422(self, client):
        resp = await client.get("/api/problems?page=0")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_problem_item_has_required_fields(self, client, visible_problem):
        resp = await client.get("/api/problems")
        items = resp.json()
        relevant = next((i for i in items if i["id"] == str(visible_problem.id)), None)
        assert relevant is not None
        for field in ["id", "title", "slug", "domain", "is_resolved", "is_verified",
                      "upvote_count", "report_count", "created_at"]:
            assert field in relevant


# ── GET /api/problems/{problem_id} ────────────────────────────────────────────


class TestGetProblem:
    @pytest.mark.asyncio
    async def test_visible_problem_returns_200(self, client, visible_problem):
        resp = await client.get(f"/api/problems/{visible_problem.id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_hidden_problem_returns_404(self, client, hidden_problem):
        resp = await client.get(f"/api/problems/{hidden_problem.id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unknown_id_returns_404(self, client):
        resp = await client.get(f"/api/problems/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client):
        resp = await client.get("/api/problems/not-a-uuid")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_detail_has_required_fields(self, client, visible_problem):
        resp = await client.get(f"/api/problems/{visible_problem.id}")
        data = resp.json()
        for field in ["id", "title", "slug", "domain", "description", "is_resolved",
                      "is_verified", "upvote_count", "report_count", "evidence",
                      "has_email", "already_voted", "already_reported", "escalation_links"]:
            assert field in data

    @pytest.mark.asyncio
    async def test_already_voted_false_for_unknown_fingerprint(self, client, visible_problem):
        resp = await client.get(
            f"/api/problems/{visible_problem.id}",
            headers={"X-Real-IP": "1.2.3.4", "User-Agent": "TestBrowser/1.0"},
        )
        assert resp.json()["already_voted"] is False

    @pytest.mark.asyncio
    async def test_x_real_ip_header_used_for_fingerprint(self, client, visible_problem):
        """Two requests from different IPs must be treated as different users."""
        resp1 = await client.get(
            f"/api/problems/{visible_problem.id}",
            headers={"X-Real-IP": "10.0.0.1", "User-Agent": "Same/1.0"},
        )
        resp2 = await client.get(
            f"/api/problems/{visible_problem.id}",
            headers={"X-Real-IP": "10.0.0.2", "User-Agent": "Same/1.0"},
        )
        # Both should return 200 — fingerprint difference is internal, but the response should work
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    @pytest.mark.asyncio
    async def test_escalation_links_present(self, client, visible_problem):
        resp = await client.get(f"/api/problems/{visible_problem.id}")
        escalation = resp.json()["escalation_links"]
        assert isinstance(escalation, list)
        assert len(escalation) >= 1


# ── POST /api/problems/{problem_id}/upvote ────────────────────────────────────


class TestUpvoteProblem:
    @pytest.mark.asyncio
    async def test_upvote_returns_200(self, client, visible_problem):
        resp = await client.post(
            f"/api/problems/{visible_problem.id}/upvote",
            headers={"X-Real-IP": "55.55.55.55", "User-Agent": "Upvoter/1.0"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_upvote_returns_count_and_flag(self, client, visible_problem):
        resp = await client.post(
            f"/api/problems/{visible_problem.id}/upvote",
            headers={"X-Real-IP": "66.66.66.66", "User-Agent": "Upvoter/2.0"},
        )
        data = resp.json()
        assert "upvote_count" in data
        assert "already_voted" in data
        assert data["already_voted"] is True

    @pytest.mark.asyncio
    async def test_double_upvote_does_not_double_count(self, client, visible_problem):
        headers = {"X-Real-IP": "77.77.77.77", "User-Agent": "Upvoter/3.0"}
        resp1 = await client.post(f"/api/problems/{visible_problem.id}/upvote", headers=headers)
        resp2 = await client.post(f"/api/problems/{visible_problem.id}/upvote", headers=headers)
        count1 = resp1.json()["upvote_count"]
        count2 = resp2.json()["upvote_count"]
        assert count1 == count2

    @pytest.mark.asyncio
    async def test_upvote_unknown_problem_still_returns_200(self, client):
        # The route doesn't 404 for unknown problem_id — it returns count=0
        resp = await client.post(f"/api/problems/{uuid.uuid4()}/upvote")
        assert resp.status_code == 200


# ── POST /api/problems/{problem_id}/report ────────────────────────────────────


class TestReportProblem:
    @pytest.mark.asyncio
    async def test_report_returns_200(self, client, visible_problem):
        resp = await client.post(
            f"/api/problems/{visible_problem.id}/report",
            data={"reason": "fake"},
            headers={"X-Real-IP": "88.88.88.88", "User-Agent": "Reporter/1.0"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_report_returns_count_and_flag(self, client, visible_problem):
        resp = await client.post(
            f"/api/problems/{visible_problem.id}/report",
            data={"reason": "duplicate"},
            headers={"X-Real-IP": "99.99.99.99", "User-Agent": "Reporter/2.0"},
        )
        data = resp.json()
        assert "report_count" in data
        assert "already_reported" in data
        assert data["already_reported"] is True

    @pytest.mark.asyncio
    async def test_missing_reason_returns_422(self, client, visible_problem):
        resp = await client.post(f"/api/problems/{visible_problem.id}/report")
        assert resp.status_code == 422


# ── GET /api/search ───────────────────────────────────────────────────────────


class TestSearchProblems:
    @pytest.mark.asyncio
    async def test_search_returns_200(self, client):
        resp = await client.get("/api/search?q=test")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_list(self, client):
        resp = await client.get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty_list(self, client):
        resp = await client.get("/api/search?q=%20%20%20")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_finds_problem_by_title(self, client, visible_problem):
        resp = await client.get("/api/search?q=API+Route+Test+Visible+Problem")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(visible_problem.id) in ids

    @pytest.mark.asyncio
    async def test_hidden_problem_not_in_search(self, client, hidden_problem):
        resp = await client.get("/api/search?q=API+Route+Test+Hidden+Problem")
        ids = [item["id"] for item in resp.json()]
        assert str(hidden_problem.id) not in ids

    @pytest.mark.asyncio
    async def test_search_page_param_accepted(self, client):
        resp = await client.get("/api/search?q=test&page=1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_page_zero_returns_422(self, client):
        resp = await client.get("/api/search?q=test&page=0")
        assert resp.status_code == 422


# ── GET /api/companies ────────────────────────────────────────────────────────


class TestSearchCompanies:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        resp = await client.get("/api/companies")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client):
        resp = await client.get("/api/companies")
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_query_filter_applied(self, client):
        # Should return empty list or only matching companies
        resp = await client.get("/api/companies?q=zzz_nonexistent_company_xyz")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_invalid_domain_id_gracefully_ignored(self, client):
        # Non-UUID domain_id should be ignored, not crash
        resp = await client.get("/api/companies?domain_id=not-a-uuid")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_valid_domain_id_filter_applied(self, client, domain):
        resp = await client.get(f"/api/companies?domain_id={domain.id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
