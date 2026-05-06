from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from agentbox import storage as _storage
from agentbox.models import Verdict, WSMessage

router = APIRouter()
_templates: Jinja2Templates | None = None


def get_templates() -> Jinja2Templates:
    global _templates
    if _templates is None:
        from pathlib import Path
        _templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "ui" / "templates"))
    return _templates


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return get_templates().TemplateResponse(request, "index.html")


@router.get("/events")
async def list_events(request: Request, status: str | None = None, limit: int = 50):
    app = request.app
    return await _storage.list_events(app.state.db_path, status=status, limit=limit)


@router.get("/events/{event_id}")
async def get_event(event_id: str, request: Request):
    app = request.app
    row = await _storage.get_event(app.state.db_path, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return row


@router.post("/verdict/{event_id}")
async def post_verdict(event_id: str, verdict: Verdict, request: Request):
    app = request.app
    resolved = datetime.now(timezone.utc).isoformat()
    ok = app.state.hitl_queue.resolve(event_id, verdict.decision)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or already resolved")

    status = "allowed" if verdict.decision == "allow" else "blocked"
    await _storage.update_verdict(
        app.state.db_path, event_id,
        status=status, verdict_by="user", resolved_at=resolved,
    )

    row = await _storage.get_event(app.state.db_path, event_id)
    if row and app.state.ws_hub:
        from agentbox.models import PromptEvent
        # broadcast verdict_set
        event_obj = PromptEvent(
            id=row["id"],
            created_at=row["created_at"],
            method=row["method"],  # type: ignore[arg-type]
            url=row["url"],
            request_headers={},
            status=status,  # type: ignore[arg-type]
        )
        await app.state.ws_hub.broadcast(
            WSMessage(type="verdict_set", event=event_obj).model_dump_json()
        )

    return {"ok": True, "status": status}


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, request: Request):
    hub = websocket.app.state.ws_hub
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)


# Dev-only seed endpoint (only registered when DEBUG=True)
@router.post("/dev/seed")
async def dev_seed(request: Request):
    import uuid
    from agentbox.models import PromptEvent
    from datetime import datetime, timezone

    app = request.app
    evt = PromptEvent(
        id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc),
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        request_headers={"content-type": "application/json"},
        request_body='{"model":"claude-3-5-sonnet","messages":[{"role":"user","content":"test"}]}',
        prompt_excerpt="test seed event",
        status="pending",
    )
    await _storage.insert_event(app.state.db_path, evt)
    app.state.hitl_queue.enqueue(evt.id)
    if app.state.ws_hub:
        await app.state.ws_hub.broadcast(
            WSMessage(type="event_created", event=evt).model_dump_json()
        )
    return {"id": evt.id}
