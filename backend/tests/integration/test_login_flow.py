import pytest


@pytest.mark.asyncio
async def test_login_correct_password(client):
    response = await client.post("/api/login", json={"password": "inha-nxt"})
    assert response.status_code == 200
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    response = await client.post("/api/login", json={"password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_cookie(client):
    response = await client.get("/api/calendar", params={"month": "2026-05"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_valid_cookie(client):
    login_resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert login_resp.status_code == 200

    response = await client.get("/api/calendar", params={"month": "2026-05"})
    assert response.status_code == 200
