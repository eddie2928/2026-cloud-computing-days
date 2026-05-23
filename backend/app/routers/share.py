from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import DiaryEntry, ShareLink
from app.schemas import SharedDiaryResponse

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{token}", response_model=SharedDiaryResponse)
async def get_shared_diary(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

    if link.expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")

    diary_res = await db.execute(
        select(DiaryEntry).where(
            DiaryEntry.user_id == link.user_id,
            DiaryEntry.diary_date == link.diary_date,
        )
    )
    entry = diary_res.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary not found")

    return SharedDiaryResponse(date=entry.diary_date, body=entry.body, emotion=entry.emotion)
