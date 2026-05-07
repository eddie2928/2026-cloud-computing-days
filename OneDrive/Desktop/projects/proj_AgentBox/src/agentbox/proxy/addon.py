import hashlib
import json
import uuid
from datetime import datetime, timezone

import grpc
from loguru import logger
from mitmproxy import http

from agentbox.config import cfg

_TARGET_HOST = "api.anthropic.com"
_TARGET_PATH = "/v1/messages"
_EXCERPT_LEN = 500


def _extract_user_id(body: str) -> str:
    """Best-effort: pull 'user' field from Claude Code request metadata."""
    try:
        data = json.loads(body)
        return str(data.get("metadata", {}).get("user_id", "unknown"))
    except Exception:
        return "unknown"


def _extract_model(body: str) -> str:
    try:
        return str(json.loads(body).get("model", ""))
    except Exception:
        return ""


class AgentBoxAddon:
    def __init__(self) -> None:
        # legacy attrs kept so existing tests still inject them without error
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
        user_id = _extract_user_id(body)
        model = _extract_model(body)
        prompt_hash = hashlib.sha256(body.encode()).hexdigest()

        logger.info("inspect_start", event_id=event_id, user_id=user_id,
                    prompt_hash=prompt_hash[:12])

        if cfg.GRPC_HOST:
            verdict, reasons = await self._grpc_inspect(event_id, body, user_id, model)
        else:
            # No EC2 configured — allow and log (development mode)
            verdict, reasons = "ALLOW", []
            logger.warning("grpc_not_configured", event_id=event_id)

        if verdict == "BLOCK":
            reason_text = "; ".join(reasons) if reasons else "blocked by policy"
            flow.response = http.Response.make(
                403, f"Blocked by AgentBox: {reason_text}".encode(),
                {"content-type": "text/plain"},
            )
            logger.info("verdict_block", event_id=event_id, reasons=reasons)
        else:
            logger.info("verdict_allow", event_id=event_id)

    async def _grpc_inspect(
        self, event_id: str, body: str, user_id: str, model: str
    ) -> tuple[str, list[str]]:
        """1B-4: Call EC2 Inspector via gRPC. On any error -> safe BLOCK."""
        try:
            from agentbox.grpc.client import inspect as grpc_inspect
            resp = grpc_inspect(user_id=user_id, prompt=body, model=model)
            verdict = resp.verdict.upper() if resp.verdict else "BLOCK"
            reasons = list(resp.reasons)
            logger.info("grpc_verdict", event_id=event_id, verdict=verdict,
                        grpc_event_id=resp.event_id)
            return verdict, reasons
        except grpc.RpcError as exc:
            logger.error("grpc_error", event_id=event_id,
                         code=exc.code(), detail=exc.details())
            return "BLOCK", ["gRPC 오류: 안전 차단"]
        except Exception as exc:
            logger.error("grpc_unexpected", event_id=event_id, error=str(exc))
            return "BLOCK", ["검사 서버 오류: 안전 차단"]
