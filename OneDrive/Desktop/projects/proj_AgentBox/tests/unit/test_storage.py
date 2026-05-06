import pytest
from datetime import datetime, timezone

from agentbox import storage as _storage
from agentbox.models import PromptEvent


def _make_event(id="evt001"):
    return PromptEvent(
        id=id,
        created_at=datetime.now(timezone.utc),
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        request_headers={"content-type": "application/json"},
        request_body='{"model":"claude-3-5-sonnet"}',
        prompt_excerpt="test prompt",
        status="pending",
    )


@pytest.mark.asyncio
async def test_init_db_idempotent(tmp_db):
    await _storage.init_db(tmp_db)
    await _storage.init_db(tmp_db)  # second call must not fail


@pytest.mark.asyncio
async def test_insert_and_list(tmp_db):
    await _storage.init_db(tmp_db)
    ev = _make_event()
    await _storage.insert_event(tmp_db, ev)
    rows = await _storage.list_events(tmp_db)
    assert len(rows) == 1
    assert rows[0]["id"] == ev.id


@pytest.mark.asyncio
async def test_list_filter_by_status(tmp_db):
    await _storage.init_db(tmp_db)
    ev1 = _make_event("e1")
    ev2 = _make_event("e2")
    await _storage.insert_event(tmp_db, ev1)
    await _storage.insert_event(tmp_db, ev2)
    await _storage.update_verdict(tmp_db, "e2", status="allowed", verdict_by="user",
                                  resolved_at=datetime.now(timezone.utc).isoformat())
    pending = await _storage.list_events(tmp_db, status="pending")
    assert len(pending) == 1 and pending[0]["id"] == "e1"
    allowed = await _storage.list_events(tmp_db, status="allowed")
    assert len(allowed) == 1 and allowed[0]["id"] == "e2"


@pytest.mark.asyncio
async def test_update_verdict(tmp_db):
    await _storage.init_db(tmp_db)
    ev = _make_event()
    await _storage.insert_event(tmp_db, ev)
    ts = datetime.now(timezone.utc).isoformat()
    await _storage.update_verdict(tmp_db, ev.id, status="blocked", verdict_by="user", resolved_at=ts)
    row = await _storage.get_event(tmp_db, ev.id)
    assert row["status"] == "blocked"
    assert row["verdict_by"] == "user"


@pytest.mark.asyncio
async def test_get_event_not_found(tmp_db):
    await _storage.init_db(tmp_db)
    row = await _storage.get_event(tmp_db, "nonexistent")
    assert row is None


@pytest.mark.asyncio
async def test_list_limit(tmp_db):
    await _storage.init_db(tmp_db)
    for i in range(5):
        await _storage.insert_event(tmp_db, _make_event(f"e{i}"))
    rows = await _storage.list_events(tmp_db, limit=3)
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_insert_multiple_and_list_all(tmp_db):
    await _storage.init_db(tmp_db)
    for i in range(3):
        await _storage.insert_event(tmp_db, _make_event(f"ev{i}"))
    rows = await _storage.list_events(tmp_db)
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_update_with_upstream_status(tmp_db):
    await _storage.init_db(tmp_db)
    ev = _make_event("eu1")
    await _storage.insert_event(tmp_db, ev)
    ts = datetime.now(timezone.utc).isoformat()
    await _storage.update_verdict(tmp_db, ev.id, status="allowed", verdict_by="user",
                                  resolved_at=ts, upstream_status_code=200)
    row = await _storage.get_event(tmp_db, ev.id)
    assert row["upstream_status_code"] == 200
