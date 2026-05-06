import asyncio


class HITLQueue:
    def __init__(self) -> None:
        self._futures: dict[str, asyncio.Future[str]] = {}

    def enqueue(self, event_id: str) -> "asyncio.Future[str]":
        fut: asyncio.Future[str] = asyncio.get_event_loop().create_future()
        self._futures[event_id] = fut
        return fut

    def resolve(self, event_id: str, verdict: str) -> bool:
        fut = self._futures.pop(event_id, None)
        if fut and not fut.done():
            fut.set_result(verdict)
            return True
        return False

    async def wait(self, event_id: str, timeout: float) -> str:
        fut = self.enqueue(event_id)
        return await asyncio.wait_for(fut, timeout=timeout)
