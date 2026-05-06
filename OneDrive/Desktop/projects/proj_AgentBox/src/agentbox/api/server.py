from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from agentbox.api.hitl import HITLQueue
from agentbox.api.ws import WSHub
from agentbox.config import cfg
from agentbox import storage as _storage


def create_app(hitl_queue: HITLQueue | None = None, ws_hub: WSHub | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await _storage.init_db(cfg.DB_PATH)
        app.state.db_path = cfg.DB_PATH
        app.state.hitl_queue = hitl_queue if hitl_queue is not None else HITLQueue()
        app.state.ws_hub = ws_hub if ws_hub is not None else WSHub()
        yield

    app = FastAPI(title="AgentBox", lifespan=lifespan)

    from agentbox.api.routes import router
    app.include_router(router)

    if cfg.DEBUG:
        pass  # /dev/seed is always included via router; gate is the DEBUG flag check in router itself

    from pathlib import Path
    static_dir = Path(__file__).parent.parent / "ui" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
