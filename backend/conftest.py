import os
import subprocess
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("CLAUDE_MODEL", "claude-sonnet-4-6")


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16") as pg:
        db_url = pg.get_connection_url().replace("psycopg2", "asyncpg")
        os.environ["DB_URL"] = db_url

        alembic_ini = os.path.join(os.path.dirname(__file__), "alembic.ini")
        subprocess.run(
            [sys.executable, "-m", "alembic", "-c", alembic_ini, "upgrade", "head"],
            env={**os.environ, "DB_URL": db_url},
            cwd=os.path.dirname(__file__),
            check=True,
        )
        yield pg, db_url


@pytest_asyncio.fixture
async def db_session(pg_container) -> AsyncGenerator[AsyncSession, None]:
    _, db_url = pg_container
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text(
                "SAVEPOINT sp_test"
            )
        )

    async with factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def app(pg_container):
    from app.config import get_settings
    from app.db import get_db
    from app.main import app as fastapi_app

    _, db_url = pg_container
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def claude_mock():
    mock_client = AsyncMock()
    mock_client.generate_question.return_value = ("오늘 어떤 일이 있었나요?", [], ["답변1", "답변2", "답변3"], {"model_id": "test"})
    mock_client.generate_diary.return_value = ("오늘 하루를 돌아보며...", "오늘 하루 요약.", {"model_id": "test"})
    mock_client.generate_plan.return_value = ("AI Plan", None, None, [], {"model_id": "test"})
    with patch("app.routers.qna._get_claude", return_value=mock_client):
        with patch("app.routers.diary.ClaudeClient", return_value=mock_client):
            with patch("app.routers.plans._get_claude", return_value=mock_client):
                yield mock_client
