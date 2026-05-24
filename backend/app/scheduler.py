import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import PushSubscription, UserProfile
from app.push import send_one

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

_sent_tracker: dict[int, str] = {}  # user_id → "YYYY-MM-DD HH:MM" already sent


def _kst_hhmm(now: datetime | None = None) -> tuple[str, str]:
    """Return (HH:MM string, YYYY-MM-DD HH:MM key) in KST."""
    kst_now = (now or datetime.now(timezone.utc)).astimezone(KST)
    hhmm = kst_now.strftime("%H:%M")
    key = kst_now.strftime("%Y-%m-%d ") + hhmm
    return hhmm, key


async def _run_notification_job(session_factory: async_sessionmaker) -> None:
    hhmm, dedup_key = _kst_hhmm()

    async with session_factory() as db:
        profiles = await _get_matching_profiles(db, hhmm)

    for user_id in profiles:
        if _sent_tracker.get(user_id) == dedup_key:
            continue

        async with session_factory() as db:
            subs = await _get_user_subscriptions(db, user_id)
            expired = []
            for sub in subs:
                should_delete = send_one(
                    endpoint=sub.endpoint,
                    p256dh=sub.p256dh,
                    auth=sub.auth,
                    payload={"title": "Days", "body": "오늘 하루를 기록해볼까요? ✍️", "url": "/"},
                )
                if should_delete:
                    expired.append(sub.id)

            if expired:
                from sqlalchemy import delete as sa_delete
                await db.execute(
                    sa_delete(PushSubscription).where(PushSubscription.id.in_(expired))
                )
                await db.commit()

        _sent_tracker[user_id] = dedup_key


async def _get_matching_profiles(db: AsyncSession, hhmm: str) -> list[int]:
    from sqlalchemy import cast, String, func as sqlfunc
    result = await db.execute(
        select(UserProfile.user_id).where(
            sqlfunc.to_char(UserProfile.notification_time, "HH24:MI") == hhmm
        )
    )
    return list(result.scalars().all())


async def _get_user_subscriptions(db: AsyncSession, user_id: int) -> list[PushSubscription]:
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    return list(result.scalars().all())


def create_scheduler() -> tuple[AsyncIOScheduler, async_sessionmaker]:
    settings = get_settings()
    engine = create_async_engine(settings.db_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        _run_notification_job,
        trigger="interval",
        minutes=1,
        args=[session_factory],
        id="push_notification",
        replace_existing=True,
    )
    return scheduler, session_factory
