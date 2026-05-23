"""Integration tests for GET /api/pet (todo #4.4)."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import Pet
from app.routers.pet import grow_pet, XP_TO_NEXT, XP_PER_DIARY


async def _login(client):
    await client.post("/api/login", json={"password": "inha-nxt"})


async def _reset_pet(db: AsyncSession, user_id: int) -> None:
    await db.execute(delete(Pet).where(Pet.user_id == user_id))
    await db.commit()


@pytest.mark.asyncio
async def test_pet_auto_create(client, db_session, pg_container):
    """GET /api/pet creates a new pet row when none exists."""
    await _login(client)
    await _reset_pet(db_session, 1)

    resp = await client.get("/api/pet")
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] >= 1
    assert data["xp"] >= 0
    assert data["xp_to_next"] == XP_TO_NEXT


@pytest.mark.asyncio
async def test_pet_xp_accumulates(client, db_session, pg_container):
    """grow_pet adds XP_PER_DIARY xp each call."""
    await _login(client)
    await _reset_pet(db_session, 1)
    await grow_pet(db_session, 1)
    await db_session.commit()

    resp = await client.get("/api/pet")
    assert resp.status_code == 200
    assert resp.json()["xp"] == XP_PER_DIARY


@pytest.mark.asyncio
async def test_pet_level_up(client, db_session, pg_container):
    """pet at xp=XP_TO_NEXT-XP_PER_DIARY after one grow → levels up, xp resets."""
    await _login(client)
    await _reset_pet(db_session, 1)

    # Set up pet at xp=XP_TO_NEXT - XP_PER_DIARY so one grow triggers level-up
    pet = Pet(user_id=1, level=1, xp=XP_TO_NEXT - XP_PER_DIARY)
    db_session.add(pet)
    await db_session.commit()

    await grow_pet(db_session, 1)
    await db_session.commit()

    resp = await client.get("/api/pet")
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] == 2
    assert data["xp"] == 0
