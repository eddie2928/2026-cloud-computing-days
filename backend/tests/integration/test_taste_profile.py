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
    "music_genres": ["K-pop", "발라드"],
    "favorite_artists": ["IU", "BTS"],
    "preferred_music_mood": ["감성적인", "신나는"],
    "mbti": "INFJ",
    "ideal_type": "따뜻한 사람",
    "personality_keywords": ["차분한", "창의적인"],
    "movie_genres": ["로맨스", "드라마"],
    "food_preferences": ["한식", "일식"],
    "life_values": ["가족", "성장"],
    "weekend_style": "조용히 집에서",
    "love_language": "함께하는 시간",
    "answers": {"q1": "yes", "q2": "no"},
    "completed": True,
}


@pytest.mark.asyncio
async def test_get_taste_profile_not_found(client, clean_taste):
    await _login(client)
    resp = await client.get("/api/taste-profile")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_taste_profile_upsert_roundtrip(client, clean_taste):
    await _login(client)
    put_resp = await client.put("/api/taste-profile", json=_TASTE_PAYLOAD)
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["music_genres"] == ["K-pop", "발라드"]
    assert data["favorite_artists"] == ["IU", "BTS"]
    assert data["preferred_music_mood"] == ["감성적인", "신나는"]
    assert data["mbti"] == "INFJ"
    assert data["ideal_type"] == "따뜻한 사람"
    assert data["personality_keywords"] == ["차분한", "창의적인"]
    assert data["movie_genres"] == ["로맨스", "드라마"]
    assert data["food_preferences"] == ["한식", "일식"]
    assert data["life_values"] == ["가족", "성장"]
    assert data["weekend_style"] == "조용히 집에서"
    assert data["love_language"] == "함께하는 시간"
    assert data["answers"] == {"q1": "yes", "q2": "no"}
    assert data["completed"] is True

    get_resp = await client.get("/api/taste-profile")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["music_genres"] == ["K-pop", "발라드"]
    assert get_data["mbti"] == "INFJ"
    assert get_data["answers"] == {"q1": "yes", "q2": "no"}
    assert get_data["completed"] is True


@pytest.mark.asyncio
async def test_put_taste_profile_unauthenticated(client):
    resp = await client.put("/api/taste-profile", json=_TASTE_PAYLOAD)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_taste_profile_unauthenticated(client):
    resp = await client.get("/api/taste-profile")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_put_taste_profile_reupsert(client, clean_taste):
    await _login(client)
    await client.put("/api/taste-profile", json=_TASTE_PAYLOAD)

    updated = {**_TASTE_PAYLOAD, "mbti": "ENFP", "music_genres": ["재즈", "힙합"]}
    resp = await client.put("/api/taste-profile", json=updated)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mbti"] == "ENFP"
    assert data["music_genres"] == ["재즈", "힙합"]
    # unchanged fields still correct
    assert data["favorite_artists"] == ["IU", "BTS"]

    get_resp = await client.get("/api/taste-profile")
    assert get_resp.status_code == 200
    assert get_resp.json()["mbti"] == "ENFP"


@pytest.mark.asyncio
async def test_put_taste_profile_empty_arrays(client, clean_taste):
    await _login(client)
    payload = {
        **_TASTE_PAYLOAD,
        "music_genres": [],
        "favorite_artists": [],
        "preferred_music_mood": [],
        "personality_keywords": [],
        "movie_genres": [],
        "food_preferences": [],
        "life_values": [],
    }
    resp = await client.put("/api/taste-profile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["music_genres"] == []
    assert data["favorite_artists"] == []
    assert data["preferred_music_mood"] == []


@pytest.mark.asyncio
async def test_put_taste_profile_none_mbti(client, clean_taste):
    await _login(client)
    payload = {**_TASTE_PAYLOAD, "mbti": None}
    resp = await client.put("/api/taste-profile", json=payload)
    assert resp.status_code == 200
    assert resp.json()["mbti"] is None


@pytest.mark.asyncio
async def test_put_taste_profile_empty_string_mbti_normalizes_to_none(client, clean_taste):
    await _login(client)
    payload = {**_TASTE_PAYLOAD, "mbti": ""}
    resp = await client.put("/api/taste-profile", json=payload)
    assert resp.status_code == 200
    assert resp.json()["mbti"] is None
