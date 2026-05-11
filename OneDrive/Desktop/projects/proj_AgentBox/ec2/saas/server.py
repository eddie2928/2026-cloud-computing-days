"""1C-5: EC2 SaaS Dashboard API - FastAPI with WebSocket pipeline stream."""
import asyncio
import json
import mimetypes
import os
import pathlib
from datetime import datetime, timezone

import boto3
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.security import APIKeyHeader
from loguru import logger
from pydantic import BaseModel

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_PROJECT = os.environ.get("PROJECT_NAME", "agentbox")
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
_POLL_INTERVAL = 2  # DynamoDB stream poll interval seconds

_dynamo = boto3.resource("dynamodb", region_name=_REGION)
_bedrock_agent_client = boto3.client("bedrock-agent", region_name=_REGION)

_api_key_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)


def _require_admin(token: str = Depends(_api_key_header)) -> str:
    if _ADMIN_TOKEN and token != _ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return token


app = FastAPI(title="AgentBox SaaS Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "saas"}


_STATIC_DIR = pathlib.Path("/opt/agentbox/ec2/saas/static")
_DASHBOARD_INDEX = _STATIC_DIR / "index.html"
_FALLBACK_HTML = (
    "<!doctype html><html><head><meta charset=utf-8>"
    "<title>AgentBox Dashboard</title></head><body>"
    "<div id=root></div>"
    "<script>document.getElementById('root').innerHTML="
    "'Dashboard not built. Run: cd dashboard && npm ci && npm run build';</script>"
    "</body></html>"
)


def _serve_spa() -> HTMLResponse:
    if _DASHBOARD_INDEX.exists():
        return HTMLResponse(_DASHBOARD_INDEX.read_text(encoding="utf-8"))
    return HTMLResponse(_FALLBACK_HTML)


@app.get("/", response_class=HTMLResponse)
async def index():
    return _serve_spa()


@app.websocket("/api/pipeline/stream")
async def pipeline_stream(websocket: WebSocket):
    """1C-5: Real-time DynamoDB poll -> WebSocket relay."""
    await websocket.accept()
    table = _dynamo.Table(f"{_PROJECT}-events")
    last_ts = datetime.now(timezone.utc).isoformat()
    try:
        while True:
            resp = table.query(
                IndexName="user_id-ts-index",
                KeyConditionExpression="ts > :ts",
                ExpressionAttributeValues={":ts": last_ts},
                Limit=20,
            ) if False else table.scan(
                FilterExpression="ts > :ts",
                ExpressionAttributeValues={":ts": last_ts},
                Limit=20,
            )
            for item in resp.get("Items", []):
                await websocket.send_text(json.dumps(item, default=str))
                last_ts = max(last_ts, item.get("ts", last_ts))
            await asyncio.sleep(_POLL_INTERVAL)
    except WebSocketDisconnect:
        pass


@app.get("/audit", response_class=HTMLResponse)
async def audit_page():
    return _serve_spa()


@app.get("/assets/{path:path}")
async def serve_asset(path: str):
    file_path = (_STATIC_DIR / "assets" / path).resolve()
    if not str(file_path).startswith(str((_STATIC_DIR / "assets").resolve())):
        raise HTTPException(status_code=403)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404)
    content_type, _ = mimetypes.guess_type(str(file_path))
    return Response(
        content=file_path.read_bytes(),
        media_type=content_type or "application/octet-stream",
    )


@app.get("/api/audit")
async def audit(
    from_ts: str | None = None,
    to_ts: str | None = None,
    verdict: str | None = None,
    limit: int = 50,
    _: str = Depends(_require_admin),
):
    """1C-5: DynamoDB events query."""
    table = _dynamo.Table(f"{_PROJECT}-events")
    filter_parts = []
    attr_values: dict = {}

    if from_ts:
        filter_parts.append("ts >= :from_ts")
        attr_values[":from_ts"] = from_ts
    if to_ts:
        filter_parts.append("ts <= :to_ts")
        attr_values[":to_ts"] = to_ts
    if verdict:
        filter_parts.append("verdict = :verdict")
        attr_values[":verdict"] = verdict.upper()

    kwargs: dict = {"Limit": limit}
    if filter_parts:
        kwargs["FilterExpression"] = " AND ".join(filter_parts)
        kwargs["ExpressionAttributeValues"] = attr_values

    resp = table.scan(**kwargs)
    return resp.get("Items", [])


class PromptSettings(BaseModel):
    system_prompt: str


@app.put("/api/settings/prompt")
async def update_prompt(body: PromptSettings, _: str = Depends(_require_admin)):
    """1C-5: Update Bedrock Agent system prompt (stored in DynamoDB settings)."""
    table = _dynamo.Table(f"{_PROJECT}-settings")
    table.put_item(Item={
        "key": "bedrock_system_prompt",
        "value": body.system_prompt,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info("prompt_updated", length=len(body.system_prompt))
    return {"ok": True}


class KBTTLSettings(BaseModel):
    ttl_minutes: int


@app.put("/api/settings/kb-ttl")
async def update_kb_ttl(body: KBTTLSettings, _: str = Depends(_require_admin)):
    """1C-5: Update KB bucket object TTL (stored in DynamoDB settings)."""
    if body.ttl_minutes < 1 or body.ttl_minutes > 60:
        raise HTTPException(status_code=422, detail="ttl_minutes must be 1-60")
    table = _dynamo.Table(f"{_PROJECT}-settings")
    table.put_item(Item={
        "key": "kb_ttl_minutes",
        "value": body.ttl_minutes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "ttl_minutes": body.ttl_minutes}


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_catch_all(full_path: str):
    return _serve_spa()


if __name__ == "__main__":
    from loguru import logger as _log
    _log.add("/opt/agentbox/logs/saas.log", rotation="50 MB")
    port = int(os.environ.get("SAAS_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
