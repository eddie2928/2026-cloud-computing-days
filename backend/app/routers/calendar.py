from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import DiaryEntry
from app.schemas import CalendarEntry, CalendarResponse

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month must be YYYY-MM format",
        )

    result = await db.execute(
        select(DiaryEntry.diary_date, DiaryEntry.emotion).where(
            DiaryEntry.user_id == user_id,
            extract("year", DiaryEntry.diary_date) == year,
            extract("month", DiaryEntry.diary_date) == mon,
        )
    )
    rows = result.all()
    entries = sorted(
        [CalendarEntry(date=row.diary_date, emotion=row.emotion) for row in rows],
        key=lambda e: e.date,
    )
    return CalendarResponse(entries=entries)
