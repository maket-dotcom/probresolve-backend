"""
Tests for category_service — requires a real DB with seeded domains.

Tests:
- get_all_domains() returns domains ordered by name
- get_categories_for_domain() returns categories filtered by domain
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models import Category, Domain
from app.services.category_service import get_all_domains, get_categories_for_domain


@pytest_asyncio.fixture
async def seeded_domain(db):
    """Fetch the first seeded domain."""
    result = await db.execute(select(Domain).limit(1))
    d = result.scalar_one_or_none()
    if d is None:
        pytest.skip("No domains seeded — run `python scripts/seed.py` first")
    return d


@pytest_asyncio.fixture
async def test_categories(db, seeded_domain):
    """Create two categories under the seeded domain and clean them up."""
    cat_a = Category(domain_id=seeded_domain.id, name="Zzz Category", slug="zzz-category")
    cat_b = Category(domain_id=seeded_domain.id, name="Aaa Category", slug="aaa-category")
    db.add(cat_a)
    db.add(cat_b)
    await db.commit()
    await db.refresh(cat_a)
    await db.refresh(cat_b)

    yield cat_a, cat_b

    await db.execute(delete(Category).where(Category.id.in_([cat_a.id, cat_b.id])))
    await db.commit()


# ── get_all_domains() ─────────────────────────────────────────────────────────


class TestGetAllDomains:
    @pytest.mark.asyncio
    async def test_returns_list(self, db, seeded_domain):
        domains = await get_all_domains(db)
        assert isinstance(domains, list)

    @pytest.mark.asyncio
    async def test_returns_at_least_one_domain(self, db, seeded_domain):
        domains = await get_all_domains(db)
        assert len(domains) >= 1

    @pytest.mark.asyncio
    async def test_domains_ordered_by_name(self, db, seeded_domain):
        domains = await get_all_domains(db)
        names = [d.name for d in domains]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_each_domain_has_required_fields(self, db, seeded_domain):
        domains = await get_all_domains(db)
        for d in domains:
            assert d.id is not None
            assert d.name
            assert d.slug
            assert d.icon


# ── get_categories_for_domain() ───────────────────────────────────────────────


class TestGetCategoriesForDomain:
    @pytest.mark.asyncio
    async def test_returns_list(self, db, seeded_domain, test_categories):
        categories = await get_categories_for_domain(db, seeded_domain.id)
        assert isinstance(categories, list)

    @pytest.mark.asyncio
    async def test_returns_categories_for_correct_domain(self, db, seeded_domain, test_categories):
        cat_a, cat_b = test_categories
        categories = await get_categories_for_domain(db, seeded_domain.id)
        ids = [c.id for c in categories]
        assert cat_a.id in ids
        assert cat_b.id in ids

    @pytest.mark.asyncio
    async def test_categories_ordered_by_name(self, db, seeded_domain, test_categories):
        categories = await get_categories_for_domain(db, seeded_domain.id)
        names = [c.name for c in categories]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_unknown_domain_returns_empty_list(self, db):
        fake_id = uuid.uuid4()
        categories = await get_categories_for_domain(db, fake_id)
        assert categories == []

    @pytest.mark.asyncio
    async def test_does_not_return_categories_from_other_domains(self, db, test_categories):
        cat_a, cat_b = test_categories
        # Get all domains, pick a different one
        all_domains = await get_all_domains(db)
        other_domains = [d for d in all_domains if d.id != cat_a.domain_id]
        if not other_domains:
            pytest.skip("Only one domain seeded — cannot test cross-domain isolation")

        other_domain = other_domains[0]
        categories = await get_categories_for_domain(db, other_domain.id)
        ids = [c.id for c in categories]
        assert cat_a.id not in ids
        assert cat_b.id not in ids
