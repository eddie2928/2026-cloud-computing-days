"""Integration tests for expire_schedules script (todo #11.1)."""
from datetime import date, timedelta

import pytest
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSchedule
from scripts.expire_schedules import expire_schedules


async def _add_schedule(
    db: AsyncSession,
    user_id: int,
    period_start: date,
    period_end: date,
    situation: str,
) -> UserSchedule:
    row = UserSchedule(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        situation=situation,
    )
    db.add(row)
    await db.flush()
    return row


@pytest.mark.asyncio
async def test_expired_schedules_replaced_with_followup(db_session, pg_container):
    """Expired records are deleted and a '마무리됨' follow-up is inserted."""
    today = date(2030, 5, 10)
    past_start = date(2030, 4, 1)
    past_end = date(2030, 5, 9)  # already expired (< today)
    user_id = 1

    await _add_schedule(db_session, user_id, past_start, past_end, "끝난 프로젝트")
    await db_session.commit()

    await expire_schedules(db_session, today)

    # Original row should be gone
    orig = await db_session.execute(
        select(UserSchedule).where(
            UserSchedule.situation == "끝난 프로젝트",
            UserSchedule.period_start == past_start,
        )
    )
    assert orig.scalar_one_or_none() is None

    # Follow-up row should exist
    followup = await db_session.execute(
        select(UserSchedule).where(
            UserSchedule.situation == "끝난 프로젝트 마무리됨",
            UserSchedule.period_start == today,
        )
    )
    row = followup.scalar_one_or_none()
    assert row is not None
    assert row.period_end == today + timedelta(days=1)


@pytest.mark.asyncio
async def test_active_schedule_not_deleted(db_session, pg_container):
    """Active schedule (today within range) is not touched."""
    today = date(2030, 6, 5)
    user_id = 1

    await _add_schedule(db_session, user_id, date(2030, 6, 1), date(2030, 6, 30), "진행 중 일정")
    await db_session.commit()

    await expire_schedules(db_session, today)

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.situation == "진행 중 일정")
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_idempotency_no_duplicate_followup(db_session, pg_container):
    """Running expire_schedules twice does not create duplicate follow-up records."""
    today = date(2030, 7, 1)
    user_id = 1

    await _add_schedule(db_session, user_id, date(2030, 6, 1), date(2030, 6, 30), "멱등성 테스트")
    await db_session.commit()

    await expire_schedules(db_session, today)
    # Run again — should not insert a second follow-up
    await expire_schedules(db_session, today)

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.situation == "멱등성 테스트 마무리됨")
    )
    rows = result.scalars().all()
    assert len(rows) == 1, "Follow-up should appear exactly once"
