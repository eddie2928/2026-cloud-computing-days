import asyncio
import uuid
from datetime import datetime, timezone

from loguru import logger
from mitmproxy import http

from agentbox.config import cfg
from agentbox.models import PromptEvent

_TARGET_HOST = "api.anthropic.com"
_TARGET_PATH = "/v1/messages"
_EXCERPT_LEN = 500


class AgentBoxAddon:
    def __init__(self) -> None:
        # Injected by server after creation
        self.hitl_queue = None
        self.ws_hub = None
        self.storage_path: str = cfg.DB_PATH

    async def request(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host != _TARGET_HOST:
            return
        if _TARGET_PATH not in flow.request.pretty_url:
            return
        await self._handle(flow)

    async def _handle(self, flow: http.HTTPFlow) -> None:
        event_id = uuid.uuid4().hex
        body = flow.request.get_text(strict=False) or ""
        excerpt = body[:_EXCERPT_LEN]

        event = PromptEvent(
            id=event_id,
            created_at=datetime.now(timezone.utc),
            source="claude_code",
            method=flow.request.method,  # type: ignore[arg-type]
            url=flow.request.pretty_url,
            request_headers=dict(flow.request.headers),
            request_body=body,
            prompt_excerpt=excerpt,
            status="pending",
        )

        from agentbox import storage as _storage
        await _storage.insert_event(self.storage_path, event)
        logger.info("event_created", event_id=event_id, url=event.url)

        if self.ws_hub:
            from agentbox.models import WSMessage
            await self.ws_hub.broadcast(WSMessage(type="event_created", event=event).model_dump_json())

        try:
            verdict = await self.hitl_queue.wait(event_id, timeout=cfg.HITL_TIMEOUT)
        except asyncio.TimeoutError:
            verdict = "block"
            await _storage.update_verdict(
                self.storage_path, event_id,
                status="failed", verdict_by="auto",
                resolved_at=datetime.now(timezone.utc).isoformat(),
                error="HITL timeout",
            )
            logger.warning("hitl_timeout", event_id=event_id)

        if verdict == "block":
            flow.response = http.Response.make(
                403, b"Blocked by AgentBox", {"content-type": "text/plain"}
            )
            logger.info("verdict_block", event_id=event_id)
        else:
            logger.info("verdict_allow", event_id=event_id)
