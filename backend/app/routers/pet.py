from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.db import get_db
from app.models import Pet
from app.schemas import PetResponse

router = APIRouter(prefix="/api/pet", tags=["pet"])

XP_PER_DIARY = 10
XP_TO_NEXT = 100


def _pet_response(pet: Pet) -> PetResponse:
    return PetResponse(level=pet.level, xp=pet.xp, xp_to_next=XP_TO_NEXT)


async def grow_pet(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(select(Pet).where(Pet.user_id == user_id))
    pet = result.scalar_one_or_none()
    if pet is None:
        pet = Pet(user_id=user_id, level=1, xp=0)
        db.add(pet)
        await db.flush()

    pet.xp += XP_PER_DIARY
    if pet.xp >= XP_TO_NEXT:
        pet.xp -= XP_TO_NEXT
        pet.level += 1
        pet.last_grew_at = datetime.now(tz=timezone.utc)


@router.get("", response_model=PetResponse)
async def get_pet(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Pet).where(Pet.user_id == user_id))
    pet = result.scalar_one_or_none()
    if pet is None:
        pet = Pet(user_id=user_id, level=1, xp=0)
        db.add(pet)
        await db.commit()
        await db.refresh(pet)
    return _pet_response(pet)
