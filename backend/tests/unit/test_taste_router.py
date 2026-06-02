"""
Unit tests for TasteProfileIn/TasteProfileOut schema validation and /api/taste-profile router.

Uses FastAPI TestClient with mocked DB session (no real DB required).
Auth is overridden to return user_id=1.
"""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("APP_PASSWORD", "test")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import require_session
from app.db import get_db
from app.routers.taste import router as taste_router
from app.schemas import TasteProfileIn, TasteProfileOut

app = FastAPI()
app.include_router(taste_router)


def make_taste(
    music_genres=None,
    favorite_artists=None,
    preferred_music_mood=None,
    mbti=None,
    ideal_type=None,
    personality_keywords=None,
    movie_genres=None,
    food_preferences=None,
    life_values=None,
    weekend_style=None,
    love_language=None,
    answers=None,
    completed=False,
):
    return SimpleNamespace(
        music_genres=music_genres or [],
        favorite_artists=favorite_artists or [],
        preferred_music_mood=preferred_music_mood or [],
        mbti=mbti,
        ideal_type=ideal_type,
        personality_keywords=personality_keywords or [],
        movie_genres=movie_genres or [],
        food_preferences=food_preferences or [],
        life_values=life_values or [],
        weekend_style=weekend_style,
        love_language=love_language,
        answers=answers,
        completed=completed,
    )


def make_db_mock(taste_obj=None):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = taste_obj

    db = AsyncMock()
    db.execute.return_value = mock_result
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)
    db.add = MagicMock()
    return db


# ── Schema unit tests ────────────────────────────────────────────────────────

class TestTasteProfileIn:
    def test_defaults(self):
        obj = TasteProfileIn()
        assert obj.music_genres == []
        assert obj.favorite_artists == []
        assert obj.preferred_music_mood == []
        assert obj.mbti is None
        assert obj.ideal_type is None
        assert obj.personality_keywords == []
        assert obj.movie_genres == []
        assert obj.food_preferences == []
        assert obj.life_values == []
        assert obj.weekend_style is None
        assert obj.love_language is None
        assert obj.answers is None
        assert obj.completed is False

    def test_mbti_empty_string_becomes_none(self):
        obj = TasteProfileIn(mbti="")
        assert obj.mbti is None

    def test_mbti_value_preserved(self):
        obj = TasteProfileIn(mbti="INFP")
        assert obj.mbti == "INFP"

    def test_array_fields_accept_lists(self):
        obj = TasteProfileIn(music_genres=["pop", "jazz"], movie_genres=["action"])
        assert obj.music_genres == ["pop", "jazz"]
        assert obj.movie_genres == ["action"]

    def test_completed_bool(self):
        obj = TasteProfileIn(completed=True)
        assert obj.completed is True

    def test_answers_dict(self):
        obj = TasteProfileIn(answers={"q1": "a1"})
        assert obj.answers == {"q1": "a1"}


class TestTasteProfileOut:
    def test_from_attributes(self):
        taste = make_taste(music_genres=["rock"], mbti="INTP", completed=True)
        out = TasteProfileOut.model_validate(taste)
        assert out.music_genres == ["rock"]
        assert out.mbti == "INTP"
        assert out.completed is True

    def test_nullable_fields_none(self):
        taste = make_taste()
        out = TasteProfileOut.model_validate(taste)
        assert out.mbti is None
        assert out.ideal_type is None
        assert out.weekend_style is None
        assert out.love_language is None
        assert out.answers is None

    def test_model_config_from_attributes(self):
        assert TasteProfileOut.model_config.get("from_attributes") is True


# ── Router integration tests (mocked DB) ────────────────────────────────────

class TestGetTasteProfile:
    def test_get_returns_404_when_not_found(self):
        db = make_db_mock(taste_obj=None)
        app.dependency_overrides[require_session] = lambda: 1
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        resp = client.get("/api/taste-profile")
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    def test_get_returns_200_when_found(self):
        taste = make_taste(music_genres=["jazz"], completed=False)
        db = make_db_mock(taste_obj=taste)
        app.dependency_overrides[require_session] = lambda: 1
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        resp = client.get("/api/taste-profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["music_genres"] == ["jazz"]
        assert data["completed"] is False
        app.dependency_overrides.clear()


class TestPutTasteProfile:
    def _put(self, taste_obj, payload):
        db = make_db_mock(taste_obj=taste_obj)

        async def _refresh(obj):
            for k, v in payload.items():
                setattr(obj, k, v)

        db.refresh = AsyncMock(side_effect=_refresh)
        app.dependency_overrides[require_session] = lambda: 1
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        resp = client.put("/api/taste-profile", json=payload)
        app.dependency_overrides.clear()
        return resp

    def test_put_creates_when_not_exists(self):
        payload = {"music_genres": ["pop"], "completed": False}
        resp = self._put(None, payload)
        assert resp.status_code == 200
        assert resp.json()["music_genres"] == ["pop"]

    def test_put_updates_existing(self):
        taste = make_taste(music_genres=["rock"])
        payload = {"music_genres": ["jazz"], "completed": True}
        resp = self._put(taste, payload)
        assert resp.status_code == 200

    def test_put_requires_auth(self):
        client = TestClient(app)
        resp = client.put("/api/taste-profile", json={})
        assert resp.status_code in (401, 403, 422)
