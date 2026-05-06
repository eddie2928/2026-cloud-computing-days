import asyncio
import pytest

from agentbox.api.hitl import HITLQueue


@pytest.mark.asyncio
async def test_wait_and_resolve():
    q = HITLQueue()
    task = asyncio.create_task(q.wait("id1", timeout=5.0))
    await asyncio.sleep(0)
    q.resolve("id1", "allow")
    result = await task
    assert result == "allow"


@pytest.mark.asyncio
async def test_resolve_returns_true():
    q = HITLQueue()
    q.enqueue("id2")
    assert q.resolve("id2", "block") is True


@pytest.mark.asyncio
async def test_resolve_nonexistent_returns_false():
    q = HITLQueue()
    assert q.resolve("no_such_id", "allow") is False


@pytest.mark.asyncio
async def test_double_resolve_second_false():
    q = HITLQueue()
    q.enqueue("id3")
    q.resolve("id3", "allow")
    assert q.resolve("id3", "block") is False


@pytest.mark.asyncio
async def test_timeout_raises():
    q = HITLQueue()
    with pytest.raises(asyncio.TimeoutError):
        await q.wait("id4", timeout=0.05)


@pytest.mark.asyncio
async def test_multiple_queued():
    q = HITLQueue()
    t1 = asyncio.create_task(q.wait("a", timeout=5.0))
    t2 = asyncio.create_task(q.wait("b", timeout=5.0))
    await asyncio.sleep(0)
    q.resolve("b", "block")
    q.resolve("a", "allow")
    assert await t1 == "allow"
    assert await t2 == "block"
