from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


def _make_async_client_mock(get_return=None, get_side_effect=None):
    """Return a mock that acts as httpx.AsyncClient async context manager."""
    mock_client = AsyncMock()
    if get_side_effect is not None:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    else:
        mock_client.get = AsyncMock(return_value=get_return)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


_FAKE_ITUNES_RESPONSE = {
    "resultCount": 2,
    "results": [
        {
            "trackName": "Blueming",
            "artistName": "IU",
            "previewUrl": "https://example.com/preview1.m4a",
            "artworkUrl100": "https://example.com/art1.jpg",
            "collectionName": "Love poem",
            "trackViewUrl": "https://example.com/track1",
            "extraField": "should_be_excluded",
        },
        {
            "trackName": "Celebrity",
            "artistName": "IU",
            "previewUrl": None,
            "artworkUrl100": "https://example.com/art2.jpg",
            "collectionName": "LILAC",
            "trackViewUrl": "https://example.com/track2",
        },
    ],
}


@pytest.mark.asyncio
async def test_music_search_success_normalized(client):
    await _login(client)
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = _FAKE_ITUNES_RESPONSE

    with patch(
        "app.routers.music.httpx.AsyncClient",
        return_value=_make_async_client_mock(get_return=fake_resp),
    ):
        resp = await client.get("/api/music/search", params={"term": "IU"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["status_code"] == 200
    assert data["count"] == 2
    assert isinstance(data["latency_ms"], int)

    r0 = data["results"][0]
    assert r0["trackName"] == "Blueming"
    assert r0["artistName"] == "IU"
    assert r0["previewUrl"] == "https://example.com/preview1.m4a"
    assert r0["artworkUrl100"] == "https://example.com/art1.jpg"
    assert r0["collectionName"] == "Love poem"
    assert "extraField" not in r0

    r1 = data["results"][1]
    assert r1["trackName"] == "Celebrity"
    assert r1["previewUrl"] is None


@pytest.mark.asyncio
async def test_music_search_external_non_200(client):
    await _login(client)
    fake_resp = MagicMock()
    fake_resp.status_code = 503

    with patch(
        "app.routers.music.httpx.AsyncClient",
        return_value=_make_async_client_mock(get_return=fake_resp),
    ):
        resp = await client.get("/api/music/search", params={"term": "IU"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["status_code"] == 503
    assert "503" in data["error"]
    assert data["results"] == []


@pytest.mark.asyncio
async def test_music_search_external_timeout(client):
    import httpx as httpx_lib

    await _login(client)
    with patch(
        "app.routers.music.httpx.AsyncClient",
        return_value=_make_async_client_mock(
            get_side_effect=httpx_lib.TimeoutException("timed out")
        ),
    ):
        resp = await client.get("/api/music/search", params={"term": "IU"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["status_code"] is None
    assert data["results"] == []


@pytest.mark.asyncio
async def test_music_search_external_network_error(client):
    await _login(client)
    with patch(
        "app.routers.music.httpx.AsyncClient",
        return_value=_make_async_client_mock(get_side_effect=Exception("Network failure")),
    ):
        resp = await client.get("/api/music/search", params={"term": "IU"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["results"] == []


@pytest.mark.asyncio
async def test_music_search_missing_term(client):
    await _login(client)
    resp = await client.get("/api/music/search")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_music_search_empty_term(client):
    await _login(client)
    resp = await client.get("/api/music/search", params={"term": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_music_search_unauthenticated(client):
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"resultCount": 0, "results": []}

    with patch(
        "app.routers.music.httpx.AsyncClient",
        return_value=_make_async_client_mock(get_return=fake_resp),
    ):
        resp = await client.get("/api/music/search", params={"term": "IU"})

    assert resp.status_code == 401
