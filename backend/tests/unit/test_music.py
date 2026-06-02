"""
@reusable
@scope project-local
@description httpx.AsyncClient async context manager를 monkeypatch하는 패턴 (_make_async_client_mock).
             FastAPI 라우터가 외부 HTTP 호출 시 AsyncClient를 사용할 때 동일하게 적용 가능.
@usage 1) _make_async_client_mock 함수를 복사  2) patch 대상을 "app.routers.{your_module}.httpx.AsyncClient"로 변경
       3) app, router, dependency override는 각 라우터에 맞게 교체
@origin proj_days / agent-task4 음원 프록시 + httpx
@created 2026-06-02
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("APP_PASSWORD", "test")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import require_session
from app.routers.music import router as music_router

app = FastAPI()
app.include_router(music_router)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _setup_client(user_id=1):
    app.dependency_overrides[require_session] = lambda: user_id
    return TestClient(app, raise_server_exceptions=True)


def _make_async_client_mock(get_return=None, get_side_effect=None):
    mock_response = get_return
    mock_client = AsyncMock()
    if get_side_effect is not None:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


class TestMusicSearchSuccess:
    def test_response_normalized_fields(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "resultCount": 1,
            "results": [
                {
                    "trackName": "Test Song",
                    "artistName": "Test Artist",
                    "previewUrl": "https://example.com/preview.m4a",
                    "artworkUrl100": "https://example.com/art.jpg",
                    "collectionName": "Test Album",
                    "trackViewUrl": "https://music.apple.com/track/123",
                    "extraField": "should_be_excluded",
                }
            ],
        }

        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(get_return=fake_resp)):
            client = _setup_client()
            resp = client.get("/api/music/search?term=test&limit=5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["status_code"] == 200
        assert data["count"] == 1
        assert isinstance(data["latency_ms"], int)
        result = data["results"][0]
        assert result["trackName"] == "Test Song"
        assert result["artistName"] == "Test Artist"
        assert result["previewUrl"] == "https://example.com/preview.m4a"
        assert result["artworkUrl100"] == "https://example.com/art.jpg"
        assert result["collectionName"] == "Test Album"
        assert result["trackViewUrl"] == "https://music.apple.com/track/123"
        assert "extraField" not in result

    def test_count_matches_results_length(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "resultCount": 3,
            "results": [
                {"trackName": f"Song{i}", "artistName": "A", "previewUrl": None,
                 "artworkUrl100": None, "collectionName": "", "trackViewUrl": None}
                for i in range(3)
            ],
        }

        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(get_return=fake_resp)):
            client = _setup_client()
            resp = client.get("/api/music/search?term=kpop")

        data = resp.json()
        assert data["ok"] is True
        assert data["count"] == 3
        assert len(data["results"]) == 3

    def test_default_limit_is_10(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"resultCount": 0, "results": []}

        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(get_return=fake_resp)) as mock_cls:
            client = _setup_client()
            client.get("/api/music/search?term=anything")

        call_kwargs = mock_cls.return_value.__aenter__.return_value.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
        assert params.get("limit") == 10


class TestMusicSearchExternalFailure:
    def test_network_error_returns_ok_false(self):
        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(get_side_effect=Exception("Network error"))):
            client = _setup_client()
            resp = client.get("/api/music/search?term=test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["status_code"] is None
        assert "Network error" in data["error"]
        assert data["results"] == []
        assert isinstance(data["latency_ms"], int)

    def test_itunes_non_200_returns_ok_false(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 503

        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(get_return=fake_resp)):
            client = _setup_client()
            resp = client.get("/api/music/search?term=test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["status_code"] == 503
        assert "503" in data["error"]
        assert data["results"] == []

    def test_timeout_error_returns_ok_false(self):
        import httpx as httpx_lib

        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(
                       get_side_effect=httpx_lib.TimeoutException("timeout"))):
            client = _setup_client()
            resp = client.get("/api/music/search?term=timeout")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["results"] == []


class TestMusicSearchInputValidation:
    def test_term_missing_returns_422(self):
        client = _setup_client()
        resp = client.get("/api/music/search")
        assert resp.status_code == 422

    def test_term_empty_returns_422(self):
        client = _setup_client()
        resp = client.get("/api/music/search?term=")
        assert resp.status_code == 422

    def test_limit_exceeds_25_returns_422(self):
        client = _setup_client()
        resp = client.get("/api/music/search?term=test&limit=26")
        assert resp.status_code == 422

    def test_limit_zero_returns_422(self):
        client = _setup_client()
        resp = client.get("/api/music/search?term=test&limit=0")
        assert resp.status_code == 422

    def test_no_auth_returns_401(self):
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/music/search?term=test")
        assert resp.status_code == 401

    def test_limit_25_allowed(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"resultCount": 0, "results": []}

        with patch("app.routers.music.httpx.AsyncClient",
                   return_value=_make_async_client_mock(get_return=fake_resp)):
            client = _setup_client()
            resp = client.get("/api/music/search?term=test&limit=25")

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
