"""
Unit tests for /api/plans router.

Uses FastAPI TestClient with mocked DB session (no real DB required).
Auth is overridden to return user_id=1.
"""
import os
from datetime import date, datetime
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
from app.routers.plans import router as plans_router

# Minimal app — avoids importing calendar.py which requires tzdata at module level
app = FastAPI()
app.include_router(plans_router)


# ── Helpers ─────────────────────────────────────────────────────────────────

def make_todo(
    id=1,
    plan_id=1,
    todo_date=date(2026, 6, 1),
    sequence=1,
    content="운동",
    completed=False,
    completed_at=None,
):
    return SimpleNamespace(
        id=id,
        plan_id=plan_id,
        todo_date=todo_date,
        sequence=sequence,
        content=content,
        completed=completed,
        completed_at=completed_at,
        created_at=datetime(2026, 6, 1, 0, 0, 0),
    )


def make_plan(
    id=1,
    user_id=1,
    title="Test Plan",
    period_start=date(2026, 6, 1),
    period_end=date(2026, 6, 30),
    source="manual",
    todos=None,
    description_input=None,
    goal_input=None,
):
    return SimpleNamespace(
        id=id,
        user_id=user_id,
        title=title,
        description_input=description_input,
        goal_input=goal_input,
        period_start=period_start,
        period_end=period_end,
        source=source,
        created_at=datetime(2026, 6, 1, 0, 0, 0),
        todos=todos if todos is not None else [],
    )


def _make_execute_result(scalars_all=None, scalars_first=None, scalar_value=None):
    """Build a mock that mimics SQLAlchemy async execute result."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = scalars_all if scalars_all is not None else []
    scalars_mock.first.return_value = scalars_first

    result = MagicMock()
    result.scalars.return_value = scalars_mock
    result.scalar.return_value = scalar_value
    return result


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _setup_client(mock_session, user_id=1):
    """Override get_db and require_session, return TestClient."""
    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_session] = lambda: user_id
    return TestClient(app, raise_server_exceptions=True)


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ── 인증 ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_list_plans_no_auth_returns_401(self):
        async def override_db():
            yield _make_session()

        app.dependency_overrides[get_db] = override_db
        # do NOT override require_session → uses real cookie check
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/plans")
        assert resp.status_code == 401

    def test_get_plan_no_auth_returns_401(self):
        async def override_db():
            yield _make_session()

        app.dependency_overrides[get_db] = override_db
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/plans/1")
        assert resp.status_code == 401


# ── GET /api/plans ────────────────────────────────────────────────────────────

class TestListPlans:
    def test_empty_list(self):
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[])
        client = _setup_client(session)
        resp = client.get("/api/plans")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_plans_with_progress(self):
        t1 = make_todo(id=1, completed=True)
        t2 = make_todo(id=2, completed=False)
        plan = make_plan(id=1, todos=[t1, t2])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[plan])
        client = _setup_client(session)
        resp = client.get("/api/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["progress"] == pytest.approx(0.5)
        assert data[0]["id"] == 1

    def test_progress_zero_when_no_todos(self):
        plan = make_plan(id=1, todos=[])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[plan])
        client = _setup_client(session)
        resp = client.get("/api/plans")
        data = resp.json()
        assert data[0]["progress"] == 0.0

    def test_progress_one_when_all_completed(self):
        todos = [make_todo(id=i, completed=True) for i in range(1, 4)]
        plan = make_plan(id=1, todos=todos)
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[plan])
        client = _setup_client(session)
        resp = client.get("/api/plans")
        assert resp.json()[0]["progress"] == pytest.approx(1.0)


# ── GET /api/plans/{plan_id} ──────────────────────────────────────────────────

class TestGetPlan:
    def test_returns_plan_with_todos(self):
        t = make_todo(id=10, content="독서")
        plan = make_plan(id=5, todos=[t])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=plan)
        client = _setup_client(session)
        resp = client.get("/api/plans/5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 5
        assert len(data["todos"]) == 1
        assert data["todos"][0]["content"] == "독서"

    def test_not_found_returns_404(self):
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=None)
        client = _setup_client(session)
        resp = client.get("/api/plans/999")
        assert resp.status_code == 404

    def test_other_user_plan_returns_404(self):
        # user_id=2 owns this plan, but authed as user_id=1
        session = _make_session()
        # DB query returns None because user_id doesn't match
        session.execute.return_value = _make_execute_result(scalars_first=None)
        client = _setup_client(session, user_id=1)
        resp = client.get("/api/plans/7")
        assert resp.status_code == 404


# ── POST /api/plans ───────────────────────────────────────────────────────────

class TestCreatePlan:
    def test_creates_plan_successfully(self):
        created_plan = make_plan(id=10, todos=[])
        session = _make_session()
        # create_plan calls execute twice: once after refresh for reload
        session.execute.side_effect = [
            _make_execute_result(scalars_first=created_plan),
        ]

        async def fake_refresh(obj):
            obj.id = 10

        session.refresh.side_effect = fake_refresh
        client = _setup_client(session)
        resp = client.post("/api/plans", json={
            "title": "6월 목표",
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Plan"  # from make_plan default
        assert "todos" in data

    def test_period_invalid_returns_400(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.post("/api/plans", json={
            "title": "잘못된 기간",
            "period_start": "2026-06-30",
            "period_end": "2026-06-01",
        })
        assert resp.status_code == 400

    def test_period_same_day_allowed(self):
        plan = make_plan(id=1, period_start=date(2026, 6, 1), period_end=date(2026, 6, 1), todos=[])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=plan)
        session.refresh = AsyncMock()
        client = _setup_client(session)
        resp = client.post("/api/plans", json={
            "title": "하루 목표",
            "period_start": "2026-06-01",
            "period_end": "2026-06-01",
        })
        assert resp.status_code == 201


# ── PUT /api/plans/{plan_id} ──────────────────────────────────────────────────

class TestUpdatePlan:
    def test_updates_title(self):
        plan = make_plan(id=1, todos=[])
        updated_plan = make_plan(id=1, title="수정된 목표", todos=[])
        session = _make_session()
        # _get_plan_or_404 → first execute
        # reload after commit → second execute
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=updated_plan),
        ]
        client = _setup_client(session)
        resp = client.put("/api/plans/1", json={"title": "수정된 목표"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "수정된 목표"

    def test_period_invalid_returns_400(self):
        plan = make_plan(id=1, todos=[])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=plan)
        client = _setup_client(session)
        resp = client.put("/api/plans/1", json={
            "period_start": "2026-06-30",
            "period_end": "2026-06-01",
        })
        assert resp.status_code == 400

    def test_not_found_returns_404(self):
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=None)
        client = _setup_client(session)
        resp = client.put("/api/plans/99", json={"title": "X"})
        assert resp.status_code == 404


# ── DELETE /api/plans/{plan_id} ───────────────────────────────────────────────

class TestDeletePlan:
    def test_deletes_plan_returns_204(self):
        plan = make_plan(id=1, todos=[make_todo()])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=plan)
        session.delete = AsyncMock()
        client = _setup_client(session)
        resp = client.delete("/api/plans/1")
        assert resp.status_code == 204
        session.delete.assert_called_once_with(plan)
        session.commit.assert_called_once()

    def test_not_found_returns_404(self):
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=None)
        client = _setup_client(session)
        resp = client.delete("/api/plans/99")
        assert resp.status_code == 404


# ── POST /api/plans/{plan_id}/todos ──────────────────────────────────────────

class TestAddTodo:
    def test_adds_todo_with_explicit_sequence(self):
        plan = make_plan(id=1, todos=[])
        todo = make_todo(id=5, plan_id=1, sequence=3, content="글쓰기")
        session = _make_session()
        # _get_plan_or_404 → plan
        # auto-assign sequence query → not called (sequence provided)
        session.execute.return_value = _make_execute_result(scalars_first=plan)

        async def fake_refresh(obj):
            obj.id = 5
            obj.plan_id = 1
            obj.todo_date = date(2026, 6, 1)
            obj.sequence = 3
            obj.content = "글쓰기"
            obj.completed = False
            obj.completed_at = None
            obj.created_at = datetime(2026, 6, 1, 0, 0, 0)

        session.refresh.side_effect = fake_refresh
        client = _setup_client(session)
        resp = client.post("/api/plans/1/todos", json={
            "todo_date": "2026-06-01",
            "sequence": 3,
            "content": "글쓰기",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["sequence"] == 3
        assert data["content"] == "글쓰기"

    def test_adds_todo_auto_sequence(self):
        plan = make_plan(id=1, todos=[])
        todo = make_todo(id=6, plan_id=1, sequence=1, content="명상")
        session = _make_session()
        # _get_plan_or_404 + auto-sequence max query
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalar_value=None),  # max sequence → None → 1
        ]

        async def fake_refresh(obj):
            obj.id = 6
            obj.plan_id = 1
            obj.todo_date = date(2026, 6, 1)
            obj.sequence = 1
            obj.content = "명상"
            obj.completed = False
            obj.completed_at = None
            obj.created_at = datetime(2026, 6, 1, 0, 0, 0)

        session.refresh.side_effect = fake_refresh
        client = _setup_client(session)
        resp = client.post("/api/plans/1/todos", json={
            "todo_date": "2026-06-01",
            "content": "명상",
        })
        assert resp.status_code == 201
        assert resp.json()["sequence"] == 1

    def test_plan_not_found_returns_404(self):
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_first=None)
        client = _setup_client(session)
        resp = client.post("/api/plans/99/todos", json={
            "todo_date": "2026-06-01",
            "content": "운동",
        })
        assert resp.status_code == 404


# ── PUT /api/plans/{plan_id}/todos/{todo_id} ──────────────────────────────────

class TestUpdateTodo:
    def test_toggles_completed_true_sets_completed_at(self):
        plan = make_plan(id=1, todos=[])
        todo = make_todo(id=10, completed=False, completed_at=None)
        session = _make_session()
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=todo),
        ]

        async def fake_refresh(obj):
            # completed_at was set by router
            pass

        session.refresh.side_effect = fake_refresh
        client = _setup_client(session)
        resp = client.put("/api/plans/1/todos/10", json={"completed": True})
        assert resp.status_code == 200
        assert todo.completed is True
        assert todo.completed_at is not None

    def test_toggles_completed_false_clears_completed_at(self):
        plan = make_plan(id=1, todos=[])
        todo = make_todo(id=10, completed=True, completed_at=datetime(2026, 6, 1, 12, 0))
        session = _make_session()
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=todo),
        ]
        session.refresh = AsyncMock()
        client = _setup_client(session)
        client.put("/api/plans/1/todos/10", json={"completed": False})
        assert todo.completed is False
        assert todo.completed_at is None

    def test_todo_plan_id_mismatch_returns_404(self):
        plan = make_plan(id=1, todos=[])
        session = _make_session()
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=None),  # todo not found (plan_id mismatch)
        ]
        client = _setup_client(session)
        resp = client.put("/api/plans/1/todos/999", json={"content": "X"})
        assert resp.status_code == 404

    def test_updates_content_and_sequence(self):
        plan = make_plan(id=1, todos=[])
        todo = make_todo(id=10, sequence=1, content="운동")
        session = _make_session()
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=todo),
        ]

        async def fake_refresh(obj):
            pass

        session.refresh.side_effect = fake_refresh
        client = _setup_client(session)
        resp = client.put("/api/plans/1/todos/10", json={"sequence": 5, "content": "수영"})
        assert resp.status_code == 200
        assert todo.sequence == 5
        assert todo.content == "수영"


# ── DELETE /api/plans/{plan_id}/todos/{todo_id} ───────────────────────────────

class TestDeleteTodo:
    def test_deletes_todo_returns_204(self):
        plan = make_plan(id=1, todos=[])
        todo = make_todo(id=10)
        session = _make_session()
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=todo),
        ]
        session.delete = AsyncMock()
        client = _setup_client(session)
        resp = client.delete("/api/plans/1/todos/10")
        assert resp.status_code == 204
        session.delete.assert_called_once_with(todo)

    def test_todo_not_found_returns_404(self):
        plan = make_plan(id=1, todos=[])
        session = _make_session()
        session.execute.side_effect = [
            _make_execute_result(scalars_first=plan),
            _make_execute_result(scalars_first=None),
        ]
        client = _setup_client(session)
        resp = client.delete("/api/plans/1/todos/999")
        assert resp.status_code == 404


# ── GET /api/plans/calendar ───────────────────────────────────────────────────

class TestCalendar:
    def test_returns_plans_overlapping_range(self):
        t_in = make_todo(id=1, todo_date=date(2026, 6, 10))
        t_out = make_todo(id=2, todo_date=date(2026, 7, 5))
        plan = make_plan(id=1, period_start=date(2026, 6, 1), period_end=date(2026, 7, 31), todos=[t_in, t_out])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[plan])
        client = _setup_client(session)
        resp = client.get("/api/plans/calendar?start=2026-06-01&end=2026-06-30")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        # Only todo within [start, end] should be in todos
        assert len(data[0]["todos"]) == 1
        assert data[0]["todos"][0]["id"] == 1

    def test_empty_when_no_overlap(self):
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[])
        client = _setup_client(session)
        resp = client.get("/api/plans/calendar?start=2026-01-01&end=2026-01-31")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_progress_uses_all_todos_not_filtered(self):
        t1 = make_todo(id=1, todo_date=date(2026, 6, 5), completed=True)
        t2 = make_todo(id=2, todo_date=date(2026, 7, 5), completed=False)
        plan = make_plan(id=1, todos=[t1, t2])
        session = _make_session()
        session.execute.return_value = _make_execute_result(scalars_all=[plan])
        client = _setup_client(session)
        resp = client.get("/api/plans/calendar?start=2026-06-01&end=2026-06-30")
        data = resp.json()
        # progress = 1/2 (all todos, not just filtered)
        assert data[0]["progress"] == pytest.approx(0.5)
        # but todos list only has t1
        assert len(data[0]["todos"]) == 1

    def test_missing_query_params_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.get("/api/plans/calendar")
        assert resp.status_code == 422
