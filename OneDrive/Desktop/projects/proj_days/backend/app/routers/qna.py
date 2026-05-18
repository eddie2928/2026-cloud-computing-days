from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_session
from app.bedrock import BedrockClient
from app.db import get_db
from app.models import QnAItem, QnASession
from app.schemas import QnAAnswerRequest, QnAAnswerResponse, QnAStartRequest, QnAStartResponse

router = APIRouter(prefix="/api/qna", tags=["qna"])

_MAX_SEQUENCE = 5


def _get_bedrock() -> BedrockClient:
    return BedrockClient()


async def _get_rag_items(db: AsyncSession, user_id: int, exclude_session_id: int) -> list[QnAItem]:
    result = await db.execute(
        select(QnAItem)
        .join(QnASession)
        .where(QnASession.user_id == user_id, QnASession.id != exclude_session_id)
        .order_by(QnAItem.asked_at.desc())
        .limit(10)
    )
    return list(result.scalars().all())


@router.post("/start", response_model=QnAStartResponse)
async def start_qna(
    body: QnAStartRequest,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QnASession)
        .options(selectinload(QnASession.items))
        .where(QnASession.user_id == user_id, QnASession.diary_date == body.diary_date)
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Diary already completed for this date",
            )
        answered_seqs = {item.sequence for item in existing.items if item.answer is not None}
        next_seq = max(answered_seqs, default=0) + 1

        unanswered = [i for i in existing.items if i.answer is None]
        if unanswered:
            unanswered.sort(key=lambda x: x.sequence)
            first_unanswered = unanswered[0]
            return QnAStartResponse(
                session_id=existing.id,
                question=first_unanswered.question,
                sequence=first_unanswered.sequence,
            )

        rag_items = await _get_rag_items(db, user_id, existing.id)
        answered_items = [i for i in existing.items if i.answer is not None]
        question, meta = await _get_bedrock().generate_question(
            rag_items, answered_items, next_seq
        )
        new_item = QnAItem(
            session_id=existing.id,
            sequence=next_seq,
            question=question,
            bedrock_meta=meta,
        )
        db.add(new_item)
        await db.commit()
        return QnAStartResponse(
            session_id=existing.id, question=question, sequence=next_seq
        )

    session = QnASession(
        user_id=user_id,
        diary_date=body.diary_date,
        status="in_progress",
    )
    db.add(session)
    await db.flush()

    rag_items = await _get_rag_items(db, user_id, session.id)
    question, meta = await _get_bedrock().generate_question(rag_items, [], 1)

    item = QnAItem(
        session_id=session.id,
        sequence=1,
        question=question,
        bedrock_meta=meta,
    )
    db.add(item)
    await db.commit()

    return QnAStartResponse(session_id=session.id, question=question, sequence=1)


@router.post("/answer", response_model=QnAAnswerResponse)
async def answer_qna(
    body: QnAAnswerRequest,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sequence"
        )

    expected_seq = max((i.sequence for i in session.items if i.answer is None), default=None)
    if expected_seq is not None and body.sequence != expected_seq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected sequence {expected_seq}, got {body.sequence}",
        )

    item.answer = body.answer
    item.answered_at = datetime.now(tz=timezone.utc)
    await db.flush()

    if body.sequence >= _MAX_SEQUENCE:
        from app.routers.diary import finalize_session

        diary_entry = await finalize_session(session, db)
        session.status = "completed"
        session.completed_at = datetime.now(tz=timezone.utc)
        await db.commit()
        return QnAAnswerResponse(completed=True, diary=diary_entry.body)

    rag_items = await _get_rag_items(db, user_id, session.id)
    answered_items = [i for i in session.items if i.answer is not None]
    next_seq = body.sequence + 1

    question, meta = await _get_bedrock().generate_question(rag_items, answered_items, next_seq)
    new_item = QnAItem(
        session_id=session.id,
        sequence=next_seq,
        question=question,
        bedrock_meta=meta,
    )
    db.add(new_item)
    await db.commit()

    return QnAAnswerResponse(next_question=question, sequence=next_seq, completed=False)
