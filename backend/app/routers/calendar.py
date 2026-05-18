from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import DiaryEntry
from app.schemas import CalendarResponse

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("", response_model=CalendarResponse)
async def get_calendar(
    month: str,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    try:
        year, mon = map(int, month.split("-"))
    except (ValueError, AttributeError):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month must be YYYY-MM format",
        )

    result = await db.execute(
        select(DiaryEntry.diary_date).where(
            DiaryEntry.user_id == user_id,
            extract("year", DiaryEntry.diary_date) == year,
            extract("month", DiaryEntry.diary_date) == mon,
        )
    )
    dates: list[date] = list(result.scalars().all())
    return CalendarResponse(dates=sorted(dates))
