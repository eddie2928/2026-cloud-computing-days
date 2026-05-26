from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import DiaryEntry, Holiday, UserSchedule
from app.schemas import CalendarEntry, CalendarResponse, HolidayOut, ScheduleOut

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

    month_first = date(year, mon, 1)
    month_last = date(year, mon, monthrange(year, mon)[1])
    sched_result = await db.execute(
        select(UserSchedule).where(
            UserSchedule.user_id == user_id,
            UserSchedule.period_start <= month_last,
            UserSchedule.period_end >= month_first,
        )
    )
    schedules = [ScheduleOut.model_validate(s) for s in sched_result.scalars().all()]

    holiday_result = await db.execute(
        select(Holiday).where(
            extract("year", Holiday.date) == year,
            extract("month", Holiday.date) == mon,
        )
    )
    holidays = [HolidayOut.model_validate(h) for h in holiday_result.scalars().all()]

    return CalendarResponse(entries=entries, schedules=schedules, holidays=holidays)
