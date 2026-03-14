"""
Tests for upvote_service.

compute_fingerprint() — pure function, no DB.
has_voted() and upvote() — require a real DB via the `db` fixture.
"""

import hashlib
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models import Domain, Problem, Upvote
from app.services.upvote_service import compute_fingerprint, has_voted, upvote


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_problem(db):
    result = await db.execute(select(Domain).limit(1))
    domain = result.scalar_one_or_none()
    if domain is None:
        pytest.skip("No domains seeded — run `python scripts/seed.py` first")

    problem = Problem(
        domain_id=domain.id,
        title="Upvote Service Test Problem",
        slug="upvote-service-test-problem",
        description="X" * 200,
    )
    db.add(problem)
    await db.commit()
    await db.refresh(problem)

    yield problem

    await db.execute(delete(Upvote).where(Upvote.problem_id == problem.id))
    await db.execute(delete(Problem).where(Problem.id == problem.id))
    await db.commit()


# ── compute_fingerprint() ─────────────────────────────────────────────────────


class TestComputeFingerprint:
    def test_returns_64_char_hex_string(self):
        fp = compute_fingerprint("1.2.3.4", "Mozilla/5.0")
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_deterministic_for_same_inputs(self):
        fp1 = compute_fingerprint("10.0.0.1", "Chrome/120")
        fp2 = compute_fingerprint("10.0.0.1", "Chrome/120")
        assert fp1 == fp2

    def test_different_ips_give_different_fingerprints(self):
        fp1 = compute_fingerprint("1.1.1.1", "SameAgent")
        fp2 = compute_fingerprint("2.2.2.2", "SameAgent")
        assert fp1 != fp2

    def test_different_user_agents_give_different_fingerprints(self):
        fp1 = compute_fingerprint("1.1.1.1", "Chrome/100")
        fp2 = compute_fingerprint("1.1.1.1", "Firefox/100")
        assert fp1 != fp2

    def test_matches_expected_sha256(self):
        ip, ua = "192.168.1.1", "TestAgent/1.0"
        expected = hashlib.sha256(f"{ip}:{ua}".encode()).hexdigest()[:64]
        assert compute_fingerprint(ip, ua) == expected

    def test_empty_strings_produce_valid_fingerprint(self):
        fp = compute_fingerprint("", "")
        assert len(fp) == 64

    def test_colon_separator_matters(self):
        # "1.2:3.4" != "1.2.3:4" — separator is the colon in ip:ua
        fp1 = compute_fingerprint("1.2", "3.4")
        fp2 = compute_fingerprint("1.2.3", "4")
        # These concatenate as "1.2:3.4" vs "1.2.3:4" — should differ
        assert fp1 != fp2


# ── has_voted() ───────────────────────────────────────────────────────────────


class TestHasVoted:
    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_fingerprint(self, db, test_problem):
        fresh_fp = "a" * 64
        result = await has_voted(db, test_problem.id, fresh_fp)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_after_vote_recorded(self, db, test_problem):
        fp = "b" * 64
        vote = Upvote(problem_id=test_problem.id, fingerprint=fp)
        db.add(vote)
        await db.commit()

        result = await has_voted(db, test_problem.id, fp)
        assert result is True

    @pytest.mark.asyncio
    async def test_different_problem_fingerprint_independent(self, db, test_problem):
        # Vote on problem A should not affect result for problem B
        fp = "c" * 64
        fake_problem_id = uuid.uuid4()
        vote = Upvote(problem_id=test_problem.id, fingerprint=fp)
        db.add(vote)
        await db.commit()

        result = await has_voted(db, fake_problem_id, fp)
        assert result is False


# ── upvote() ──────────────────────────────────────────────────────────────────


class TestUpvote:
    @pytest.mark.asyncio
    async def test_first_upvote_increments_count(self, db, test_problem):
        fp = "d" * 64
        count, already_voted = await upvote(db, test_problem.id, fp)
        assert count == 1
        assert already_voted is True

    @pytest.mark.asyncio
    async def test_duplicate_upvote_does_not_increment(self, db, test_problem):
        fp = "e" * 64
        count1, _ = await upvote(db, test_problem.id, fp)
        count2, already = await upvote(db, test_problem.id, fp)
        assert count2 == count1
        assert already is True

    @pytest.mark.asyncio
    async def test_multiple_unique_fingerprints_accumulate(self, db, test_problem):
        fps = ["f" * 64, "1" * 64, "2" * 64]
        for i, fp in enumerate(fps):
            count, _ = await upvote(db, test_problem.id, fp)
            assert count == i + 1

    @pytest.mark.asyncio
    async def test_returns_already_voted_true_after_cast(self, db, test_problem):
        fp = "g" * 64
        _, already_voted = await upvote(db, test_problem.id, fp)
        assert already_voted is True

    @pytest.mark.asyncio
    async def test_already_voted_is_true_on_duplicate(self, db, test_problem):
        fp = "h" * 64
        await upvote(db, test_problem.id, fp)
        _, already_voted = await upvote(db, test_problem.id, fp)
        assert already_voted is True
