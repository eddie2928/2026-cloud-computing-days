from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import TasteProfile
from app.schemas import TasteProfileIn, TasteProfileOut

router = APIRouter(prefix="/api", tags=["taste"])


@router.get("/taste-profile", response_model=TasteProfileOut)
async def get_taste_profile(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TasteProfile).where(TasteProfile.user_id == user_id))
    taste = result.scalar_one_or_none()
    if taste is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taste profile not found")
    return taste


@router.put("/taste-profile", response_model=TasteProfileOut)
async def upsert_taste_profile(
    body: TasteProfileIn,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TasteProfile).where(TasteProfile.user_id == user_id))
    taste = result.scalar_one_or_none()

    if taste is None:
        taste = TasteProfile(user_id=user_id)
        db.add(taste)

    taste.music_genres = body.music_genres
    taste.favorite_artists = body.favorite_artists
    taste.preferred_music_mood = body.preferred_music_mood
    taste.mbti = body.mbti
    taste.ideal_type = body.ideal_type
    taste.personality_keywords = body.personality_keywords
    taste.movie_genres = body.movie_genres
    taste.food_preferences = body.food_preferences
    taste.life_values = body.life_values
    taste.weekend_style = body.weekend_style
    taste.love_language = body.love_language
    taste.answers = body.answers
    taste.completed = body.completed

    await db.commit()
    await db.refresh(taste)
    return taste
