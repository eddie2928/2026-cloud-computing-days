from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import DiaryEntry
from app.schemas import StreakResponse
from app.time_kst import kst_today

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
) -> StreakResponse:
    today = kst_today()
    streak = 0
    check_date = today
    while True:
        result = await db.execute(
            select(DiaryEntry).where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.diary_date == check_date,
            )
        )
        if result.scalar_one_or_none() is None:
            break
        streak += 1
        check_date -= timedelta(days=1)
    return StreakResponse(streak=streak)
