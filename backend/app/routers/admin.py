from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db

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
