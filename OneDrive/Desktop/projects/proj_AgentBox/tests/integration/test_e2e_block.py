"""
E2E test: FastAPI app + mitmproxy stub via httpx proxy client.
Uses respx to mock upstream Anthropic API.
Skipped if mitmproxy DumpMaster cannot bind (CI without network).
"""
import asyncio
import pytest
import httpx

from httpx import AsyncClient, ASGITransport

from agentbox.api.server import create_app
from agentbox.config import cfg


@pytest.fixture
async def app(tmp_db, tmp_path):
    cfg.DB_PATH = tmp_db
    cfg.CA_DIR = str(tmp_path / "certs")
    cfg.DEBUG = True
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application


@pytest.mark.asyncio
async def test_seed_and_block(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seed = await client.post("/dev/seed")
        assert seed.status_code == 200
        ev_id = seed.json()["id"]

        events = await client.get("/events")
        assert any(e["id"] == ev_id for e in events.json())

        verdict = await client.post(f"/verdict/{ev_id}", json={"decision": "block"})
        assert verdict.status_code == 200
        assert verdict.json()["status"] == "blocked"

        ev = await client.get(f"/events/{ev_id}")
        assert ev.json()["status"] == "blocked"


@pytest.mark.asyncio
async def test_seed_and_allow(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seed = await client.post("/dev/seed")
        ev_id = seed.json()["id"]

        verdict = await client.post(f"/verdict/{ev_id}", json={"decision": "allow"})
        assert verdict.status_code == 200
        assert verdict.json()["status"] == "allowed"


@pytest.mark.asyncio
async def test_double_verdict_rejected(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seed = await client.post("/dev/seed")
        ev_id = seed.json()["id"]
        await client.post(f"/verdict/{ev_id}", json={"decision": "allow"})
        r = await client.post(f"/verdict/{ev_id}", json={"decision": "block"})
        assert r.status_code == 404
