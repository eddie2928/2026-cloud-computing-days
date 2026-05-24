from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import QnAItem

router = APIRouter(prefix="/api/admin", tags=["admin"])

_ALLOWED_TABLES = {
    "users",
    "user_profiles",
    "qna_sessions",
    "qna_items",
    "diary_entries",
    "pet",
    "share_links",
    "user_schedules",
}


@router.get("/tables")
async def list_tables(user_id: int = Depends(require_session)) -> list[str]:
    return sorted(_ALLOWED_TABLES)


@router.get("/bedrock-logs")
async def get_bedrock_logs(
    limit: int = 50,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(QnAItem)
        .order_by(QnAItem.asked_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    logs = []
    for item in items:
        meta = item.bedrock_meta or {}
        logs.append({
            "id": item.id,
            "session_id": item.session_id,
            "sequence": item.sequence,
            "question": item.question,
            "asked_at": item.asked_at.isoformat() if item.asked_at else None,
            "prompt": meta.get("prompt"),
            "raw_response": meta.get("raw_response"),
            "model_id": meta.get("model_id"),
            "input_tokens": meta.get("input_tokens"),
            "output_tokens": meta.get("output_tokens"),
            "latency_ms": meta.get("latency_ms"),
        })
    return logs


@router.get("/tables/{name}")
async def get_table_rows(
    name: str,
    limit: int = 100,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if name not in _ALLOWED_TABLES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Table '{name}' not found")
    result = await db.execute(text(f"SELECT * FROM {name} LIMIT :limit"), {"limit": limit})
    rows = result.mappings().all()
    return [dict(row) for row in rows]
