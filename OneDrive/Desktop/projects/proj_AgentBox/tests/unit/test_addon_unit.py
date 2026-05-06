import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agentbox.proxy.addon import AgentBoxAddon
from agentbox.api.hitl import HITLQueue


def _make_flow(host="api.anthropic.com", method="POST", body=b'{"model":"test"}'):
    flow = MagicMock()
    flow.request.pretty_host = host
    flow.request.pretty_url = f"https://{host}/v1/messages"
    flow.request.method = method
    flow.request.headers = {"content-type": "application/json"}
    flow.request.get_text.return_value = body.decode()
    flow.response = None
    return flow


@pytest.mark.asyncio
async def test_non_target_passthrough(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)
    addon = AgentBoxAddon()
    addon.hitl_queue = HITLQueue()
    addon.ws_hub = None
    addon.storage_path = tmp_db
    flow = _make_flow(host="example.com")
    await addon.request(flow)
    assert flow.response is None


@pytest.mark.asyncio
async def test_allow_verdict_no_response(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolve_after():
        await asyncio.sleep(0.01)
        # find the pending event id and resolve it
        rows = await _storage.list_events(tmp_db, status="pending")
        if rows:
            queue.resolve(rows[0]["id"], "allow")

    await asyncio.gather(addon._handle(flow), resolve_after())
    assert flow.response is None


@pytest.mark.asyncio
async def test_block_verdict_sets_403(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolve_after():
        await asyncio.sleep(0.01)
        rows = await _storage.list_events(tmp_db, status="pending")
        if rows:
            queue.resolve(rows[0]["id"], "block")

    await asyncio.gather(addon._handle(flow), resolve_after())
    assert flow.response is not None
    assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_timeout_causes_block(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    with patch.object(addon, '_handle', wraps=addon._handle):
        # patch timeout to 0.05s
        import agentbox.proxy.addon as addon_mod
        orig_timeout = addon_mod.cfg.HITL_TIMEOUT
        addon_mod.cfg.HITL_TIMEOUT = 0.05
        try:
            await addon._handle(flow)
        finally:
            addon_mod.cfg.HITL_TIMEOUT = orig_timeout

    assert flow.response is not None
    assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_event_stored_on_intercept(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = None
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolve_after():
        await asyncio.sleep(0.01)
        rows = await _storage.list_events(tmp_db, status="pending")
        if rows:
            queue.resolve(rows[0]["id"], "allow")

    await asyncio.gather(addon._handle(flow), resolve_after())
    rows = await _storage.list_events(tmp_db)
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_ws_broadcast_called(tmp_db):
    from agentbox import storage as _storage
    await _storage.init_db(tmp_db)

    queue = HITLQueue()
    hub = AsyncMock()
    addon = AgentBoxAddon()
    addon.hitl_queue = queue
    addon.ws_hub = hub
    addon.storage_path = tmp_db

    flow = _make_flow()

    async def resolve_after():
        await asyncio.sleep(0.01)
        rows = await _storage.list_events(tmp_db, status="pending")
        if rows:
            queue.resolve(rows[0]["id"], "allow")

    await asyncio.gather(addon._handle(flow), resolve_after())
    hub.broadcast.assert_called_once()
