from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_session
from app.bedrock import BedrockClient
from app.db import get_db
from app.models import DiaryEntry, QnAItem, QnASession, UserProfile
from app.schemas import QnAAnswerRequest, QnAAnswerResponse, QnAStartRequest, QnAStartResponse

router = APIRouter(prefix="/api/qna", tags=["qna"])

_MAX_SEQUENCE = 5


def _get_bedrock() -> BedrockClient:
    return BedrockClient()


async def _get_user_profile(db: AsyncSession, user_id: int) -> dict | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return {
        "nickname": profile.nickname,
        "occupation": profile.occupation,
        "hobbies": profile.hobbies,
        "interests": profile.interests,
    }


async def _get_rag_items(db: AsyncSession, user_id: int, exclude_session_id: int) -> list[QnAItem]:
    result = await db.execute(
        select(QnAItem)
        .join(QnASession)
        .where(QnASession.user_id == user_id, QnASession.id != exclude_session_id)
        .order_by(QnAItem.asked_at.desc())
        .limit(10)
    )
    return list(result.scalars().all())


async def _resume_session(
    existing: QnASession, db: AsyncSession, user_id: int, user_profile: dict | None = None
) -> QnAStartResponse:
    if existing.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Diary already completed for this date",
        )
    unanswered = sorted(
        [i for i in existing.items if i.answer is None], key=lambda x: x.sequence
    )
    if unanswered:
        first = unanswered[0]
        return QnAStartResponse(
            session_id=existing.id, question=first.question, sequence=first.sequence
        )
    answered_seqs = {i.sequence for i in existing.items if i.answer is not None}
    next_seq = max(answered_seqs, default=0) + 1
    session_id = existing.id
    answered_items = [i for i in existing.items if i.answer is not None]
    rag_items = await _get_rag_items(db, user_id, session_id)
    question, meta = await _get_bedrock().generate_question(rag_items, answered_items, next_seq, user_profile=user_profile)
    try:
        db.add(QnAItem(session_id=session_id, sequence=next_seq, question=question, bedrock_meta=meta))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        res = await db.execute(
            select(QnAItem).where(QnAItem.session_id == session_id, QnAItem.sequence == next_seq)
        )
        ei = res.scalar_one()
        question, next_seq = ei.question, ei.sequence
    return QnAStartResponse(session_id=session_id, question=question, sequence=next_seq)


@router.post("/start", response_model=QnAStartResponse)
async def start_qna(
    body: QnAStartRequest,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    user_profile = await _get_user_profile(db, user_id)
    result = await db.execute(
        select(QnASession)
        .options(selectinload(QnASession.items))
        .where(QnASession.user_id == user_id, QnASession.diary_date == body.diary_date)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return await _resume_session(existing, db, user_id, user_profile=user_profile)

    # Commit session BEFORE Bedrock call to close the race window where concurrent
    # requests both see no existing session and both try to INSERT.
    session = QnASession(user_id=user_id, diary_date=body.diary_date, status="in_progress")
    db.add(session)
    try:
        await db.flush()
        session_id = session.id
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(QnASession)
            .options(selectinload(QnASession.items))
            .where(QnASession.user_id == user_id, QnASession.diary_date == body.diary_date)
        )
        return await _resume_session(result.scalar_one(), db, user_id, user_profile=user_profile)

    rag_items = await _get_rag_items(db, user_id, session_id)
    question, meta = await _get_bedrock().generate_question(rag_items, [], 1, user_profile=user_profile)
    try:
        db.add(QnAItem(session_id=session_id, sequence=1, question=question, bedrock_meta=meta))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        res = await db.execute(
            select(QnAItem).where(QnAItem.session_id == session_id, QnAItem.sequence == 1)
        )
        ei = res.scalar_one()
        question = ei.question
    return QnAStartResponse(session_id=session_id, question=question, sequence=1)


@router.post("/answer", response_model=QnAAnswerResponse)
async def answer_qna(
    body: QnAAnswerRequest,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    user_profile = await _get_user_profile(db, user_id)
    result = await db.execute(
        select(QnASession)
        .options(selectinload(QnASession.items))
        .where(QnASession.id == body.session_id, QnASession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    item = next((i for i in session.items if i.sequence == body.sequence), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sequence")

    # Idempotency: duplicate submit or concurrent race where this answer already committed.
    if item.answer is not None:
        if session.status == "completed":
            diary_res = await db.execute(
                select(DiaryEntry).where(DiaryEntry.session_id == session.id)
            )
            diary = diary_res.scalar_one_or_none()
            return QnAAnswerResponse(completed=True, diary=diary.body if diary else None)
        next_items = sorted(
            [i for i in session.items if i.answer is None], key=lambda x: x.sequence
        )
        if next_items:
            return QnAAnswerResponse(
                next_question=next_items[0].question,
                sequence=next_items[0].sequence,
                completed=False,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Answer already submitted"
        )

    expected_seq = max(
        (i.sequence for i in session.items if i.answer is None), default=None
    )
    if expected_seq is not None and body.sequence != expected_seq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected sequence {expected_seq}, got {body.sequence}",
        )

    # Snapshot what we need before commit — SQLAlchemy expires all attributes after commit().
    item.answer = body.answer
    item.answered_at = datetime.now(tz=timezone.utc)
    session_id = session.id
    is_final = body.sequence >= _MAX_SEQUENCE
    answered_snapshot = [i for i in session.items if i.answer is not None]

    await db.flush()
    await db.commit()  # commit before any Bedrock call to close race window

    if is_final:
        from app.routers.diary import finalize_session

        try:
            diary_entry = await finalize_session(session_id, db, user_profile=user_profile)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            diary_res = await db.execute(
                select(DiaryEntry).where(DiaryEntry.session_id == session_id)
            )
            diary_entry = diary_res.scalar_one()
        return QnAAnswerResponse(completed=True, diary=diary_entry.body)

    next_seq = body.sequence + 1
    rag_items = await _get_rag_items(db, user_id, session_id)
    question, meta = await _get_bedrock().generate_question(rag_items, answered_snapshot, next_seq, user_profile=user_profile)

    try:
        db.add(QnAItem(session_id=session_id, sequence=next_seq, question=question, bedrock_meta=meta))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        res = await db.execute(
            select(QnAItem).where(
                QnAItem.session_id == session_id, QnAItem.sequence == next_seq
            )
        )
        ei = res.scalar_one()
        question, next_seq = ei.question, ei.sequence

    return QnAAnswerResponse(next_question=question, sequence=next_seq, completed=False)
