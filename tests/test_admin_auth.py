"""
Tests for admin auth.
All routes check ?key= BEFORE touching the DB, so 403 tests need no DB setup.
test_correct_key_does_not_return_403 hits the real DB (via NullPool override in conftest).
"""

import pytest

from app.config import settings

CORRECT_KEY = settings.admin_key
WRONG_KEY = "definitely-wrong-key-xyz"

ADMIN_ROUTES_POST = [
    "/admin/problems/00000000-0000-0000-0000-000000000001/verify",
    "/admin/problems/00000000-0000-0000-0000-000000000001/hide",
    "/admin/problems/00000000-0000-0000-0000-000000000001/resolve",
    "/admin/problems/00000000-0000-0000-0000-000000000001/clear-flags",
    "/admin/problems/00000000-0000-0000-0000-000000000001/delete",
]


class TestAdminAuth:
    @pytest.mark.asyncio
    async def test_admin_dashboard_no_key_returns_403(self, client):
        resp = await client.get("/admin")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_dashboard_wrong_key_returns_403(self, client):
        resp = await client.get(f"/admin?key={WRONG_KEY}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ADMIN_ROUTES_POST)
    async def test_admin_post_no_key_returns_403(self, client, path):
        resp = await client.post(path)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ADMIN_ROUTES_POST)
    async def test_admin_post_wrong_key_returns_403(self, client, path):
        resp = await client.post(f"{path}?key={WRONG_KEY}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_correct_key_loads_dashboard(self, client):
        """Correct key passes auth and dashboard renders (may have 0 complaints)."""
        resp = await client.get(f"/admin?key={CORRECT_KEY}")
        assert resp.status_code == 200
        assert "Admin Dashboard" in resp.text
