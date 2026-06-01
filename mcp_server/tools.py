import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models import (
    DiaryEntry,
    QnASession,
    User,
    UserSchedule,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _ok(data) -> dict:
    return {"status": "ok", "data": data}


def _err(code: str, message: str) -> dict:
    return {"status": "error", "code": code, "message": message}


def _validate_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _user_row(user: User) -> dict:
    p = user.profile
    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "created_at": user.created_at.isoformat(),
        "profile": {
            "nickname": p.nickname,
            "gender": p.gender,
            "age": p.age,
            "occupation": p.occupation,
            "hobbies": p.hobbies,
            "interests": p.interests,
        } if p is not None else None,
    }


# ── list_users ────────────────────────────────────────────────────────────────

async def list_users(session: AsyncSession) -> dict:
    result = await session.execute(
        select(User).options(selectinload(User.profile))
    )
    users = result.scalars().all()
    return _ok([_user_row(u) for u in users])


# ── get_user_info ─────────────────────────────────────────────────────────────

async def get_user_info(session: AsyncSession, user_id: int) -> dict:
    result = await session.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return _err("USER_NOT_FOUND", f"No user with id={user_id}")
    return _ok(_user_row(user))


# ── list_diaries ──────────────────────────────────────────────────────────────

async def list_diaries(session: AsyncSession, user_id: int,
                       date_from: str, date_to: str) -> dict:
    d_from = _validate_date(date_from)
    d_to = _validate_date(date_to)
    if d_from is None or d_to is None:
        return _err("INVALID_DATE", "date_from and date_to must be YYYY-MM-DD")

    user = await session.get(User, user_id)
    if user is None:
        return _err("USER_NOT_FOUND", f"No user with id={user_id}")

    result = await session.execute(
        select(DiaryEntry)
        .where(DiaryEntry.user_id == user_id)
        .where(DiaryEntry.diary_date >= d_from)
        .where(DiaryEntry.diary_date <= d_to)
        .order_by(DiaryEntry.diary_date)
    )
    entries = result.scalars().all()
    return _ok([
        {
            "diary_date": e.diary_date.isoformat(),
            "emotion": e.emotion,
            "summary": e.summary,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ])


# ── get_emotion_trend ─────────────────────────────────────────────────────────

async def get_emotion_trend(session: AsyncSession, user_id: int,
                             date_from: str, date_to: str) -> dict:
    d_from = _validate_date(date_from)
    d_to = _validate_date(date_to)
    if d_from is None or d_to is None:
        return _err("INVALID_DATE", "date_from and date_to must be YYYY-MM-DD")

    user = await session.get(User, user_id)
    if user is None:
        return _err("USER_NOT_FOUND", f"No user with id={user_id}")

    result = await session.execute(
        select(DiaryEntry.diary_date, DiaryEntry.emotion)
        .where(DiaryEntry.user_id == user_id)
        .where(DiaryEntry.diary_date >= d_from)
        .where(DiaryEntry.diary_date <= d_to)
        .order_by(DiaryEntry.diary_date)
    )
    rows = result.all()
    return _ok([
        {"diary_date": r.diary_date.isoformat(), "emotion": r.emotion}
        for r in rows
    ])


# ── get_diary_session ─────────────────────────────────────────────────────────

async def get_diary_session(session: AsyncSession, user_id: int, date: str) -> dict:
    d = _validate_date(date)
    if d is None:
        return _err("INVALID_DATE", "date must be YYYY-MM-DD")

    user = await session.get(User, user_id)
    if user is None:
        return _err("USER_NOT_FOUND", f"No user with id={user_id}")

    result = await session.execute(
        select(QnASession)
        .options(
            selectinload(QnASession.items),
            selectinload(QnASession.diary_entry),
        )
        .where(QnASession.user_id == user_id)
        .where(QnASession.diary_date == d)
    )
    qna = result.scalar_one_or_none()
    if qna is None:
        return _ok(None)

    diary = qna.diary_entry
    return _ok({
        "diary_date": qna.diary_date.isoformat(),
        "status": qna.status,
        "completed_at": qna.completed_at.isoformat() if qna.completed_at else None,
        "qna_items": sorted(
            [
                {
                    "sequence": item.sequence,
                    "question": item.question,
                    "answer": item.answer,
                    "asked_at": item.asked_at.isoformat(),
                    "answered_at": item.answered_at.isoformat() if item.answered_at else None,
                }
                for item in qna.items
            ],
            key=lambda x: x["sequence"],
        ),
        "diary": {
            "body": diary.body,
            "summary": diary.summary,
            "emotion": diary.emotion,
            "created_at": diary.created_at.isoformat(),
        } if diary is not None else None,
    })


# ── get_user_schedules ────────────────────────────────────────────────────────

async def get_user_schedules(session: AsyncSession, user_id: int,
                              date_from: str | None, date_to: str | None) -> dict:
    d_from = None
    d_to = None

    if date_from is not None:
        d_from = _validate_date(date_from)
        if d_from is None:
            return _err("INVALID_DATE", "date_from must be YYYY-MM-DD")

    if date_to is not None:
        d_to = _validate_date(date_to)
        if d_to is None:
            return _err("INVALID_DATE", "date_to must be YYYY-MM-DD")

    user = await session.get(User, user_id)
    if user is None:
        return _err("USER_NOT_FOUND", f"No user with id={user_id}")

    stmt = (
        select(UserSchedule)
        .where(UserSchedule.user_id == user_id)
        .order_by(UserSchedule.period_start)
    )

    if d_from is not None:
        stmt = stmt.where(UserSchedule.period_end >= d_from)

    if d_to is not None:
        stmt = stmt.where(UserSchedule.period_start <= d_to)

    result = await session.execute(stmt)
    schedules = result.scalars().all()
    return _ok([
        {
            "id": s.id,
            "period_start": s.period_start.isoformat(),
            "period_end": s.period_end.isoformat(),
            "situation": s.situation,
            "created_at": s.created_at.isoformat(),
        }
        for s in schedules
    ])
