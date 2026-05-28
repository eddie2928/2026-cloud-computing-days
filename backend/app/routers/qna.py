import json
from datetime import date, datetime, timedelta, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_session
# NOTE: BedrockClient는 현재 bedrock_stub의 BedrockStubClient로 re-export됨 (수동 마이그레이션 기간).
from app.bedrock import BedrockClient, _parse_schedules
from app.db import get_db
from app.models import DiaryEntry, QnAItem, QnASession, UserProfile, UserSchedule
from app.schemas import PendingSchedule, QnAAnswerRequest, QnAAnswerResponse, QnAFinalizeRequest, QnAFinalizeResponse, QnAHistoryItem, QnAStartRequest, QnAStartResponse, QnAUndoRequest, QnAUndoResponse

router = APIRouter(prefix="/api/qna", tags=["qna"])

_MIN_SEQUENCE = 5


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


async def _get_recent_summaries(
    db: AsyncSession, user_id: int, diary_date: date, days: int = 30
) -> list[tuple[date, str]]:
    start = diary_date - timedelta(days=days)
    end = diary_date - timedelta(days=1)
    result = await db.execute(
        select(DiaryEntry.diary_date, DiaryEntry.summary)
        .where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.diary_date >= start,
            DiaryEntry.diary_date <= end,
        )
        .order_by(DiaryEntry.diary_date.desc())
    )
    return list(result.all())


async def _get_relevant_schedules(db: AsyncSession, user_id: int, today: date) -> list[str]:
    cutoff = today - timedelta(days=7)
    result = await db.execute(
        select(UserSchedule)
        .where(
            UserSchedule.user_id == user_id,
            UserSchedule.period_end >= cutoff,
        )
    )
    schedules = result.scalars().all()
    labels: list[str] = []
    for s in schedules:
        if s.period_end >= today:
            labels.append(f"[진행중] {s.situation} ({s.period_start}~{s.period_end})")
        else:
            days_ago = (today - s.period_end).days
            labels.append(f"[{days_ago}일 전 종료] {s.situation} ({s.period_start}~{s.period_end})")
    return labels



def _build_previously_extracted(items: list[QnAItem]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for item in items:
        meta = item.bedrock_meta
        if not meta or not meta.get("raw_response"):
            continue
        for s in _parse_schedules(meta["raw_response"]):
            key = f"{s['period_start']}|{s['period_end']}|{s['situation']}"
            if key not in seen:
                seen.add(key)
                lines.append(key)
    return "\n".join(lines)


def _to_pending_schedules(extracted: list[dict]) -> list[PendingSchedule]:
    result = []
    for sched in extracted:
        try:
            ps = PendingSchedule(
                period_start=sched["period_start"],
                period_end=sched["period_end"],
                situation=sched.get("situation", "").strip(),
            )
            if ps.situation:
                result.append(ps)
        except (KeyError, ValueError):
            continue
    return result


async def _resume_session(
    existing: QnASession, db: AsyncSession, user_id: int, user_profile: dict | None = None
) -> QnAStartResponse:
    if existing.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Diary already completed for this date",
        )
    answered_items = sorted(
        [i for i in existing.items if i.answer is not None], key=lambda x: x.sequence
    )
    history = [
        QnAHistoryItem(sequence=i.sequence, question=i.question, answer=i.answer)
        for i in answered_items
    ]
    unanswered = sorted(
        [i for i in existing.items if i.answer is None], key=lambda x: x.sequence
    )
    if unanswered:
        first = unanswered[0]
        rag_summaries = await _get_recent_summaries(db, user_id, existing.diary_date)
        relevant_scheds = await _get_relevant_schedules(db, user_id, existing.diary_date)
        prev_extracted = _build_previously_extracted(answered_items)
        question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(
            rag_summaries, answered_items, first.sequence,
            user_profile=user_profile, relevant_schedules=relevant_scheds,
            today=existing.diary_date, previously_extracted=prev_extracted,
        )
        pending = _to_pending_schedules(extracted_schedules)
        first.question = question
        first.bedrock_meta = meta
        await db.commit()
        return QnAStartResponse(
            session_id=existing.id, question=question, sequence=first.sequence,
            history=history, pending_schedules=pending, suggestions=suggestions,
        )
    next_seq = max((i.sequence for i in answered_items), default=0) + 1
    session_id = existing.id
    rag_summaries = await _get_recent_summaries(db, user_id, existing.diary_date)
    relevant_scheds = await _get_relevant_schedules(db, user_id, existing.diary_date)
    prev_extracted = _build_previously_extracted(answered_items)
    question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(rag_summaries, answered_items, next_seq, user_profile=user_profile, relevant_schedules=relevant_scheds, today=existing.diary_date, previously_extracted=prev_extracted)
    pending = _to_pending_schedules(extracted_schedules)
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
        pending = []
        suggestions = []
    return QnAStartResponse(session_id=session_id, question=question, sequence=next_seq, history=history, pending_schedules=pending, suggestions=suggestions)


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

    rag_summaries = await _get_recent_summaries(db, user_id, body.diary_date)
    relevant_scheds = await _get_relevant_schedules(db, user_id, body.diary_date)
    question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(rag_summaries, [], 1, user_profile=user_profile, relevant_schedules=relevant_scheds, today=body.diary_date)
    pending = _to_pending_schedules(extracted_schedules)
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
        pending = []
        suggestions = []
    return QnAStartResponse(session_id=session_id, question=question, sequence=1, pending_schedules=pending, suggestions=suggestions)


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

    expected_seq = min(
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
    diary_date = session.diary_date
    min_reached = body.sequence >= _MIN_SEQUENCE
    answered_snapshot = [i for i in session.items if i.answer is not None]

    await db.flush()
    await db.commit()  # commit before any Bedrock call to close race window

    next_seq = body.sequence + 1
    rag_summaries = await _get_recent_summaries(db, user_id, diary_date)
    relevant_scheds = await _get_relevant_schedules(db, user_id, diary_date)
    prev_extracted = _build_previously_extracted(answered_snapshot)
    question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(rag_summaries, answered_snapshot, next_seq, user_profile=user_profile, relevant_schedules=relevant_scheds, today=diary_date, previously_extracted=prev_extracted)
    pending = _to_pending_schedules(extracted_schedules)

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
        pending = []
        suggestions = []

    return QnAAnswerResponse(next_question=question, sequence=next_seq, completed=False, pending_schedules=pending, suggestions=suggestions, min_reached=min_reached)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/start-stream")
async def start_qna_stream(
    body: QnAStartRequest,
    request: Request,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    async def _generate() -> AsyncGenerator[str, None]:
        user_profile = await _get_user_profile(db, user_id)
        result = await db.execute(
            select(QnASession)
            .options(selectinload(QnASession.items))
            .where(QnASession.user_id == user_id, QnASession.diary_date == body.diary_date)
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status == "completed":
                yield _sse_event("error", {"detail": "Diary already completed for this date", "status_code": 409})
                return

            answered_items = sorted(
                [i for i in existing.items if i.answer is not None], key=lambda x: x.sequence
            )
            history = [
                QnAHistoryItem(sequence=i.sequence, question=i.question, answer=i.answer)
                for i in answered_items
            ]
            unanswered = sorted(
                [i for i in existing.items if i.answer is None], key=lambda x: x.sequence
            )

            yield _sse_event("status", {"step": "schedules"})
            relevant_scheds = await _get_relevant_schedules(db, user_id, existing.diary_date)
            yield _sse_event("status", {"step": "summaries"})
            rag_summaries = await _get_recent_summaries(db, user_id, existing.diary_date)

            if unanswered:
                first = unanswered[0]
                prev_extracted = _build_previously_extracted(answered_items)
                yield _sse_event("status", {"step": "generating"})
                question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(
                    rag_summaries, answered_items, first.sequence,
                    user_profile=user_profile, relevant_schedules=relevant_scheds,
                    today=existing.diary_date, previously_extracted=prev_extracted,
                )
                pending = _to_pending_schedules(extracted_schedules)
                first.question = question
                first.bedrock_meta = meta
                await db.commit()
                resp = QnAStartResponse(
                    session_id=existing.id, question=question, sequence=first.sequence,
                    history=history, pending_schedules=pending, suggestions=suggestions,
                )
            else:
                next_seq = max((i.sequence for i in answered_items), default=0) + 1
                prev_extracted = _build_previously_extracted(answered_items)
                yield _sse_event("status", {"step": "generating"})
                question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(
                    rag_summaries, answered_items, next_seq,
                    user_profile=user_profile, relevant_schedules=relevant_scheds,
                    today=existing.diary_date, previously_extracted=prev_extracted,
                )
                pending = _to_pending_schedules(extracted_schedules)
                try:
                    db.add(QnAItem(session_id=existing.id, sequence=next_seq, question=question, bedrock_meta=meta))
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    res = await db.execute(
                        select(QnAItem).where(QnAItem.session_id == existing.id, QnAItem.sequence == next_seq)
                    )
                    ei = res.scalar_one()
                    question, next_seq = ei.question, ei.sequence
                    pending = []
                    suggestions = []
                resp = QnAStartResponse(
                    session_id=existing.id, question=question, sequence=next_seq,
                    history=history, pending_schedules=pending, suggestions=suggestions,
                )
            yield _sse_event("done", resp.model_dump())
            return

        # New session
        session = QnASession(user_id=user_id, diary_date=body.diary_date, status="in_progress")
        db.add(session)
        try:
            await db.flush()
            session_id = session.id
            await db.commit()
        except IntegrityError:
            await db.rollback()
            result2 = await db.execute(
                select(QnASession)
                .options(selectinload(QnASession.items))
                .where(QnASession.user_id == user_id, QnASession.diary_date == body.diary_date)
            )
            existing2 = result2.scalar_one()
            # Delegate to resume path by re-invoking stream logic (simplified: yield from resume)
            if existing2.status == "completed":
                yield _sse_event("error", {"detail": "Diary already completed for this date", "status_code": 409})
                return
            answered_items2 = sorted(
                [i for i in existing2.items if i.answer is not None], key=lambda x: x.sequence
            )
            history2 = [
                QnAHistoryItem(sequence=i.sequence, question=i.question, answer=i.answer)
                for i in answered_items2
            ]
            unanswered2 = sorted(
                [i for i in existing2.items if i.answer is None], key=lambda x: x.sequence
            )
            yield _sse_event("status", {"step": "schedules"})
            relevant_scheds2 = await _get_relevant_schedules(db, user_id, existing2.diary_date)
            yield _sse_event("status", {"step": "summaries"})
            rag_summaries2 = await _get_recent_summaries(db, user_id, existing2.diary_date)
            if unanswered2:
                first2 = unanswered2[0]
                prev2 = _build_previously_extracted(answered_items2)
                yield _sse_event("status", {"step": "generating"})
                q2, es2, sug2, m2 = await _get_bedrock().generate_question(
                    rag_summaries2, answered_items2, first2.sequence,
                    user_profile=user_profile, relevant_schedules=relevant_scheds2,
                    today=existing2.diary_date, previously_extracted=prev2,
                )
                first2.question = q2
                first2.bedrock_meta = m2
                await db.commit()
                resp2 = QnAStartResponse(
                    session_id=existing2.id, question=q2, sequence=first2.sequence,
                    history=history2, pending_schedules=_to_pending_schedules(es2), suggestions=sug2,
                )
            else:
                nseq2 = max((i.sequence for i in answered_items2), default=0) + 1
                prev2 = _build_previously_extracted(answered_items2)
                yield _sse_event("status", {"step": "generating"})
                q2, es2, sug2, m2 = await _get_bedrock().generate_question(
                    rag_summaries2, answered_items2, nseq2,
                    user_profile=user_profile, relevant_schedules=relevant_scheds2,
                    today=existing2.diary_date, previously_extracted=prev2,
                )
                try:
                    db.add(QnAItem(session_id=existing2.id, sequence=nseq2, question=q2, bedrock_meta=m2))
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    res2 = await db.execute(
                        select(QnAItem).where(QnAItem.session_id == existing2.id, QnAItem.sequence == nseq2)
                    )
                    ei2 = res2.scalar_one()
                    q2, nseq2 = ei2.question, ei2.sequence
                    sug2 = []
                resp2 = QnAStartResponse(
                    session_id=existing2.id, question=q2, sequence=nseq2,
                    history=history2, pending_schedules=_to_pending_schedules(es2), suggestions=sug2,
                )
            yield _sse_event("done", resp2.model_dump())
            return

        yield _sse_event("status", {"step": "schedules"})
        relevant_scheds = await _get_relevant_schedules(db, user_id, body.diary_date)
        yield _sse_event("status", {"step": "summaries"})
        rag_summaries = await _get_recent_summaries(db, user_id, body.diary_date)
        yield _sse_event("status", {"step": "generating"})
        question, extracted_schedules, suggestions, meta = await _get_bedrock().generate_question(
            rag_summaries, [], 1, user_profile=user_profile,
            relevant_schedules=relevant_scheds, today=body.diary_date,
        )
        pending = _to_pending_schedules(extracted_schedules)
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
            pending = []
            suggestions = []
        resp = QnAStartResponse(session_id=session_id, question=question, sequence=1, pending_schedules=pending, suggestions=suggestions)
        yield _sse_event("done", resp.model_dump())

    return StreamingResponse(_generate(), media_type="text/event-stream")
