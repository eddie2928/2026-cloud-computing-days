import asyncio
from unittest.mock import MagicMock, AsyncMock
import pytest

from agentbox.api.hitl import HITLQueue
from agentbox.proxy.addon import AgentBoxAddon


def _make_flow(host="api.anthropic.com"):
    flow = MagicMock()
    flow.request.pretty_host = host
    flow.request.pretty_url = f"https://{host}/v1/messages"
    flow.request.method = "POST"
    flow.request.headers = {"content-type": "application/json"}
    flow.request.get_text.return_value = '{"model":"claude-3-5-sonnet"}'
    flow.response = None
    return flow


@pytest.mark.asyncio
async def test_allow_flow(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolver():
        await asyncio.sleep(0.02)
        rows = await _storage.list_events(tmp_db, status="pending")
        assert len(rows) == 1
        queue.resolve(rows[0]["id"], "allow")

    await asyncio.gather(addon._handle(flow), resolver())
    assert flow.response is None


@pytest.mark.asyncio
async def test_block_flow(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolver():
        await asyncio.sleep(0.02)
        rows = await _storage.list_events(tmp_db, status="pending")
        queue.resolve(rows[0]["id"], "block")

    await asyncio.gather(addon._handle(flow), resolver())
    assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_db_status_after_allow(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolver():
        await asyncio.sleep(0.02)
        rows = await _storage.list_events(tmp_db, status="pending")
        eid = rows[0]["id"]
        queue.resolve(eid, "allow")
        # simulate API updating verdict
        from datetime import datetime, timezone
        await _storage.update_verdict(tmp_db, eid, status="allowed",
                                      verdict_by="user",
                                      resolved_at=datetime.now(timezone.utc).isoformat())

    await asyncio.gather(addon._handle(flow), resolver())
    rows = await _storage.list_events(tmp_db, status="allowed")
    assert len(rows) == 1
