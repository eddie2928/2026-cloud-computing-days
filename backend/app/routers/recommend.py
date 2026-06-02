from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import TasteProfile
from app.recommend_stub import recommend_songs

router = APIRouter(prefix="/api", tags=["recommend"])


@router.get("/recommend/songs")
async def get_recommended_songs(
    limit: int = 5,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TasteProfile).where(TasteProfile.user_id == user_id))
    taste = result.scalar_one_or_none()

    if taste is None:
        return {
            "items": [],
            "meta": {"source": "stub", "note": "취향 프로필을 먼저 작성해 주세요."},
        }

    taste_dict = {
        "music_genres": taste.music_genres,
        "preferred_music_mood": taste.preferred_music_mood,
        "favorite_artists": taste.favorite_artists,
    }

    return recommend_songs(taste_dict, limit=limit)
