import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


@pytest_asyncio.fixture
async def clean_taste(pg_container):
    """Delete all taste_profiles before test to guarantee clean state."""
    _, db_url = pg_container
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM taste_profiles"))
    await engine.dispose()


_TASTE_PAYLOAD = {
    "music_genres": ["K-pop"],
    "favorite_artists": ["IU"],
    "preferred_music_mood": ["감성적인"],
    "mbti": None,
    "ideal_type": None,
    "personality_keywords": [],
    "movie_genres": [],
    "food_preferences": [],
    "life_values": [],
    "weekend_style": None,
    "love_language": None,
    "answers": None,
    "completed": True,
}


@pytest.mark.asyncio
async def test_recommend_songs_unauthenticated(client):
    resp = await client.get("/api/recommend/songs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_recommend_songs_no_taste(client, clean_taste):
    await _login(client)
    resp = await client.get("/api/recommend/songs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert "meta" in data
    assert "note" in data["meta"]


@pytest.mark.asyncio
async def test_recommend_songs_with_taste(client, clean_taste):
    await _login(client)
    put_resp = await client.put("/api/taste-profile", json=_TASTE_PAYLOAD)
    assert put_resp.status_code == 200

    resp = await client.get("/api/recommend/songs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert "meta" in data
    assert data["meta"]["source"] == "stub"


@pytest.mark.asyncio
async def test_recommend_songs_deterministic(client, clean_taste):
    await _login(client)
    await client.put("/api/taste-profile", json=_TASTE_PAYLOAD)

    resp1 = await client.get("/api/recommend/songs")
    resp2 = await client.get("/api/recommend/songs")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
