import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from agentbox.api.server import create_app
from agentbox.config import cfg


@pytest.fixture
async def app(tmp_db):
    cfg.DB_PATH = tmp_db
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_index_returns_html(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "AgentBox" in r.text


@pytest.mark.asyncio
async def test_events_empty(client):
    r = await client.get("/events")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_events_after_seed(client, app):
    r = await client.post("/dev/seed")
    assert r.status_code == 200
    ev_id = r.json()["id"]
    r2 = await client.get("/events")
    assert len(r2.json()) == 1
    assert r2.json()[0]["id"] == ev_id


@pytest.mark.asyncio
async def test_get_event_not_found(client):
    r = await client.get("/events/no_such_id")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_verdict_allow(client, app):
    seed = await client.post("/dev/seed")
    ev_id = seed.json()["id"]
    r = await client.post(f"/verdict/{ev_id}", json={"decision": "allow"})
    assert r.status_code == 200
    assert r.json()["status"] == "allowed"


@pytest.mark.asyncio
async def test_verdict_block(client, app):
    seed = await client.post("/dev/seed")
    ev_id = seed.json()["id"]
    r = await client.post(f"/verdict/{ev_id}", json={"decision": "block"})
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


@pytest.mark.asyncio
async def test_verdict_double_returns_404(client, app):
    seed = await client.post("/dev/seed")
    ev_id = seed.json()["id"]
    await client.post(f"/verdict/{ev_id}", json={"decision": "allow"})
    r2 = await client.post(f"/verdict/{ev_id}", json={"decision": "block"})
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_verdict_nonexistent_404(client):
    r = await client.post("/verdict/no_such_id", json={"decision": "allow"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_events_filter_by_status(client, app):
    s1 = await client.post("/dev/seed")
    s2 = await client.post("/dev/seed")
    await client.post(f"/verdict/{s1.json()['id']}", json={"decision": "allow"})
    r = await client.get("/events?status=pending")
    ids = [e["id"] for e in r.json()]
    assert s2.json()["id"] in ids
    assert s1.json()["id"] not in ids
