import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import admin, auth, calendar, diary, insights, pet, plans, profile, push, qna, schedules, share, user
from app.scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler, _ = create_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="QnA Diary API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(qna.router)
app.include_router(diary.router)
app.include_router(calendar.router)
app.include_router(profile.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(pet.router)
app.include_router(schedules.router)
app.include_router(insights.router)
app.include_router(plans.router)
app.include_router(share.router)
app.include_router(push.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_FRONTEND_DIST):
    _assets_dir = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="static-assets")

    @app.get("/{full_path:path}")
    async def _spa_fallback(full_path: str):
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
