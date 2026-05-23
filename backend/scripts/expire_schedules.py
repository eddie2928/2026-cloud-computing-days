"""Cron script: expire past user_schedules and insert follow-up 'completed' records.

Runs daily at KST 23:50 via EC2 cron.
Idempotent: duplicate follow-up records are skipped.
"""
import asyncio
import os
import sys
from datetime import date, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models import UserSchedule


async def expire_schedules(db: AsyncSession, today_kst: date) -> None:
    result = await db.execute(
        select(UserSchedule).where(UserSchedule.period_end < today_kst)
    )
    expired = result.scalars().all()

    for row in expired:
        followup_situation = f"{row.situation} 마무리됨"
        dup_check = await db.execute(
            select(UserSchedule).where(
                UserSchedule.user_id == row.user_id,
                UserSchedule.period_start == today_kst,
                UserSchedule.period_end == today_kst + timedelta(days=1),
                UserSchedule.situation == followup_situation,
            )
        )
        if dup_check.scalar_one_or_none() is None:
            db.add(UserSchedule(
                user_id=row.user_id,
                period_start=today_kst,
                period_end=today_kst + timedelta(days=1),
                situation=followup_situation,
            ))
        await db.delete(row)

    await db.commit()


async def main() -> None:
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL environment variable not set")

    today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await expire_schedules(session, today_kst)
    await engine.dispose()
    print(f"expire_schedules completed for {today_kst}")


if __name__ == "__main__":
    asyncio.run(main())
