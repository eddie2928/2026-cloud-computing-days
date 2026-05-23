"""Integration tests for /api/admin endpoints (todo #12.1)."""
import pytest


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_unauthorized_without_login(client):
    """GET /api/admin/tables returns 401 when not logged in."""
    resp = await client.get("/api/admin/tables")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_tables_returns_rows_when_logged_in(client):
    """GET /api/admin/tables/users returns 200 and a list after login."""
    await _login(client)
    resp = await client.get("/api/admin/tables/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_admin_unknown_table_returns_404(client):
    """GET /api/admin/tables/<unlisted> returns 404."""
    await _login(client)
    resp = await client.get("/api/admin/tables/secret_internal_table")
    assert resp.status_code == 404
