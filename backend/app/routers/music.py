import time

import httpx
from fastapi import APIRouter, Depends, Query

from app.auth import require_session

router = APIRouter(prefix="/api/music", tags=["music"])

_ITUNES_URL = "https://itunes.apple.com/search"


@router.get("/search")
async def search_music(
    term: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=25),
    user_id: int = Depends(require_session),
):
    params = {
        "term": term,
        "media": "music",
        "limit": limit,
        "country": "KR",
    }
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_ITUNES_URL, params=params)
        latency_ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code != 200:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "latency_ms": latency_ms,
                "error": f"iTunes returned {resp.status_code}",
                "results": [],
            }
        raw = resp.json()
        results = [
            {
                "trackName": item.get("trackName", ""),
                "artistName": item.get("artistName", ""),
                "previewUrl": item.get("previewUrl"),
                "artworkUrl100": item.get("artworkUrl100"),
                "collectionName": item.get("collectionName", ""),
                "trackViewUrl": item.get("trackViewUrl"),
            }
            for item in raw.get("results", [])
        ]
        return {
            "ok": True,
            "status_code": 200,
            "latency_ms": latency_ms,
            "count": len(results),
            "results": results,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc),
            "results": [],
        }
