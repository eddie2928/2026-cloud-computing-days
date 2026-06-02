from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import UserSchedule
from app.schemas import ScheduleConfirm, ScheduleOut, ScheduleUpdate

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleOut])
async def get_schedules(
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

    month_first = date(year, mon, 1)
    month_last = date(year, mon, monthrange(year, mon)[1])

    result = await db.execute(
        select(UserSchedule).where(
            UserSchedule.user_id == user_id,
            UserSchedule.period_start <= month_last,
            UserSchedule.period_end >= month_first,
        )
    )
    schedules = result.scalars().all()
    return schedules


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    body: ScheduleConfirm,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(UserSchedule).where(
            UserSchedule.user_id == user_id,
            UserSchedule.period_start == body.period_start,
            UserSchedule.period_end == body.period_end,
            UserSchedule.situation == body.situation,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate schedule",
        )

    schedule = UserSchedule(
        user_id=user_id,
        period_start=body.period_start,
        period_end=body.period_end,
        start_time=body.start_time,
        end_time=body.end_time,
        situation=body.situation,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(
    schedule_id: int,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSchedule).where(
            UserSchedule.id == schedule_id,
            UserSchedule.user_id == user_id,
        )
    )
    schedule = result.scalars().first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")
    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSchedule).where(
            UserSchedule.id == schedule_id,
            UserSchedule.user_id == user_id,
        )
    )
    schedule = result.scalars().first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")

    if body.period_start is not None:
        schedule.period_start = body.period_start
    if body.period_end is not None:
        schedule.period_end = body.period_end
    if body.start_time is not None:
        schedule.start_time = body.start_time
    if body.end_time is not None:
        schedule.end_time = body.end_time
    if body.situation is not None:
        schedule.situation = body.situation

    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSchedule).where(
            UserSchedule.id == schedule_id,
            UserSchedule.user_id == user_id,
        )
    )
    schedule = result.scalars().first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")

    await db.delete(schedule)
    await db.commit()
