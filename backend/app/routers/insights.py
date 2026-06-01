import sys
from pathlib import Path

# mcp_server is at the monorepo root, two levels above backend/
_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
import mcp_server.tools as mcp_tools

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/diaries")
async def list_diaries(
    date_from: str,
    date_to: str,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    return await mcp_tools.list_diaries(db, user_id, date_from, date_to)


@router.get("/diaries/{date}")
async def get_diary_session(
    date: str,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    return await mcp_tools.get_diary_session(db, user_id, date)


@router.get("/emotion-trend")
async def get_emotion_trend(
    date_from: str,
    date_to: str,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    return await mcp_tools.get_emotion_trend(db, user_id, date_from, date_to)


@router.get("/schedules")
async def get_user_schedules(
    date_from: str | None = None,
    date_to: str | None = None,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    return await mcp_tools.get_user_schedules(db, user_id, date_from, date_to)
