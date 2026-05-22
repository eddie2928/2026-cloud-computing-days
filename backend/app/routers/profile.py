from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import UserProfile
from app.schemas import UserProfileIn, UserProfileOut

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile", response_model=UserProfileOut)
async def get_profile(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("/profile", response_model=UserProfileOut)
async def upsert_profile(
    body: UserProfileIn,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    profile.nickname = body.nickname
    profile.gender = body.gender
    profile.age = body.age
    profile.occupation = body.occupation
    profile.hobbies = body.hobbies
    profile.interests = body.interests
    profile.notification_time = body.notification_time

    await db.commit()
    await db.refresh(profile)
    return profile
