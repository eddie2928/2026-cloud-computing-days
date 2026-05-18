from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_session
from app.bedrock import BedrockClient
from app.db import get_db
from app.models import DiaryEntry, QnASession
from app.schemas import DiaryResponse

router = APIRouter(prefix="/api/diary", tags=["diary"])


async def finalize_session(session_id: int, db: AsyncSession) -> DiaryEntry:
    # Re-query with fresh items so this is safe to call after a preceding commit()
    # that would have expired the caller's session object.
    result = await db.execute(
        select(QnASession)
        .options(selectinload(QnASession.items))
        .where(QnASession.id == session_id)
    )
    session = result.scalar_one()

    client = BedrockClient()
    diary_body, meta = await client.generate_diary(session.items)

    entry = DiaryEntry(
        session_id=session.id,
        user_id=session.user_id,
        diary_date=session.diary_date,
        body=diary_body,
        bedrock_meta=meta,
    )
    db.add(entry)
    session.status = "completed"
    session.completed_at = datetime.now(tz=timezone.utc)
    await db.flush()
    return entry


@router.get("/{diary_date}", response_model=DiaryResponse)
async def get_diary(
    diary_date: date,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DiaryEntry).where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.diary_date == diary_date,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary not found")
    return DiaryResponse(date=entry.diary_date, body=entry.body)
