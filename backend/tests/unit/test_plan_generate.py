"""
Unit tests for POST /api/plans/generate (T03).

Uses FastAPI TestClient with mocked DB session (no real DB required).
Auth is overridden to return user_id=1.
"""
import asyncio
import os
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("APP_PASSWORD", "test")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import require_session
from app.db import get_db
from app.routers.plans import router as plans_router

app = FastAPI()
app.include_router(plans_router)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_todo(
    id=1, plan_id=1, todo_date=date(2026, 6, 1), sequence=1, content="아침 루틴",
    completed=False, completed_at=None,
):
    return SimpleNamespace(
        id=id, plan_id=plan_id, todo_date=todo_date, sequence=sequence,
        content=content, completed=completed, completed_at=completed_at,
        created_at=datetime(2026, 6, 1, 0, 0, 0),
    )


def make_plan(
    id=1, user_id=1, title="AI Plan", period_start=date(2026, 6, 1),
    period_end=date(2026, 6, 3), source="ai", todos=None,
    description_input=None, goal_input=None, ai_meta=None,
):
    return SimpleNamespace(
        id=id, user_id=user_id, title=title,
        description_input=description_input, goal_input=goal_input,
        period_start=period_start, period_end=period_end,
        source=source, ai_meta=ai_meta,
        created_at=datetime(2026, 6, 1, 0, 0, 0),
        todos=todos if todos is not None else [],
    )


def _make_execute_result(
    scalars_all=None, scalars_first=None,
    scalar_value=None, scalar_one_or_none=None,
):
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = scalars_all if scalars_all is not None else []
    scalars_mock.first.return_value = scalars_first

    result = MagicMock()
    result.scalars.return_value = scalars_mock
    result.scalar.return_value = scalar_value
    result.scalar_one_or_none.return_value = scalar_one_or_none
    return result


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _setup_client(mock_session, user_id=1):
    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_session] = lambda: user_id
    return TestClient(app, raise_server_exceptions=True)


_VALID_BODY = {
    "description": "운동 루틴",
    "period_start": "2026-06-01",
    "period_end": "2026-06-03",
    "goal": "건강 유지",
}

_STUB_DAYS = [
    {"date": date(2026, 6, 1), "todos": ["아침 루틴", "핵심 작업", "마무리 회고"]},
    {"date": date(2026, 6, 2), "todos": ["아침 루틴", "핵심 작업", "마무리 회고"]},
    {"date": date(2026, 6, 3), "todos": ["아침 루틴", "핵심 작업", "마무리 회고"]},
]

_STUB_META = {
    "model_id": "stub", "input_tokens": 0, "output_tokens": 0,
    "latency_ms": 0, "prompt": "stub", "raw_response": "<stub>",
}


# ── 인증 ──────────────────────────────────────────────────────────────────────

class TestGeneratePlanAuth:
    def test_no_auth_returns_401(self):
        async def override_db():
            yield _make_session()

        app.dependency_overrides[get_db] = override_db
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post("/api/plans/generate", json=_VALID_BODY)
        assert resp.status_code == 401


# ── 입력 검증 ─────────────────────────────────────────────────────────────────

class TestGeneratePlanValidation:
    def test_description_too_long_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.post("/api/plans/generate", json={
            **_VALID_BODY,
            "description": "x" * 2001,
        })
        assert resp.status_code == 422

    def test_description_empty_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.post("/api/plans/generate", json={
            **_VALID_BODY,
            "description": "",
        })
        assert resp.status_code == 422

    def test_goal_too_long_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.post("/api/plans/generate", json={
            **_VALID_BODY,
            "goal": "x" * 501,
        })
        assert resp.status_code == 422

    def test_goal_empty_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.post("/api/plans/generate", json={
            **_VALID_BODY,
            "goal": "",
        })
        assert resp.status_code == 422

    def test_period_end_before_start_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        resp = client.post("/api/plans/generate", json={
            **_VALID_BODY,
            "period_start": "2026-06-30",
            "period_end": "2026-06-01",
        })
        assert resp.status_code == 422

    def test_period_over_90_days_returns_422(self):
        session = _make_session()
        client = _setup_client(session)
        # 2026-06-01 to 2026-09-01 = 92 days difference
        resp = client.post("/api/plans/generate", json={
            **_VALID_BODY,
            "period_start": "2026-06-01",
            "period_end": "2026-09-01",
        })
        assert resp.status_code == 422

    def test_period_exactly_90_days_allowed(self):
        """period_end - period_start = 90 days is allowed."""
        session = _make_session()
        # 2026-06-01 to 2026-08-30 = 90 days difference → allowed
        plan = make_plan(id=1, todos=[])
        session.execute.side_effect = [
            _make_execute_result(scalar_one_or_none=None),
            _make_execute_result(scalars_first=plan),
        ]
        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "AI Plan", date(2026, 6, 1), date(2026, 8, 30), [], _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            resp = client.post("/api/plans/generate", json={
                **_VALID_BODY,
                "period_start": "2026-06-01",
                "period_end": "2026-08-30",
            })
        assert resp.status_code == 201


# ── Stub 직접 테스트 ───────────────────────────────────────────────────────────

class TestBedrockStubGeneratePlan:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_generates_correct_day_count(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        _, _, _, days, _ = self._run(client.generate_plan(
            description="운동 루틴 만들기",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 3),
            goal="건강",
        ))
        assert len(days) == 3

    def test_each_day_has_3_todos(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        _, _, _, days, _ = self._run(client.generate_plan(
            description="계획",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 5),
            goal="목표",
        ))
        for day in days:
            assert "date" in day
            assert "todos" in day
            assert len(day["todos"]) == 3

    def test_single_day_plan(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        _, _, _, days, _ = self._run(client.generate_plan(
            description="하루 계획",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 1),
            goal="목표",
        ))
        assert len(days) == 1

    def test_title_truncation_over_14_chars(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        long_desc = "이것은 매우 긴 계획 설명입니다"
        title, *_ = self._run(client.generate_plan(
            description=long_desc,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 1),
            goal="목표",
        ))
        assert "…" in title
        assert len(title) <= 15

    def test_title_kept_when_14_chars_or_less(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        short_desc = "운동루틴"
        title, *_ = self._run(client.generate_plan(
            description=short_desc,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 1),
            goal="목표",
        ))
        assert title == short_desc
        assert "…" not in title

    def test_meta_format(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        _, _, _, _, meta = self._run(client.generate_plan(
            description="계획",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 1),
            goal="목표",
        ))
        assert meta == _STUB_META

    def test_period_preserved(self):
        from app.bedrock_stub import BedrockStubClient
        client = BedrockStubClient()
        ps = date(2026, 7, 1)
        pe = date(2026, 7, 10)
        _, ret_ps, ret_pe, _, _ = self._run(client.generate_plan(
            description="계획",
            period_start=ps,
            period_end=pe,
            goal="목표",
        ))
        assert ret_ps == ps
        assert ret_pe == pe


# ── 엔드포인트 성공 케이스 ─────────────────────────────────────────────────────

class TestGeneratePlanEndpoint:
    def _setup(self, todos=None):
        session = _make_session()
        if todos is None:
            todos = [
                make_todo(id=i + 1, sequence=(i % 3) + 1,
                          todo_date=date(2026, 6, (i // 3) + 1),
                          content=["아침 루틴", "핵심 작업", "마무리 회고"][i % 3])
                for i in range(9)
            ]
        plan = make_plan(id=10, title="운동 루틴", source="ai", todos=todos,
                         description_input="운동 루틴", goal_input="건강 유지")
        session.execute.side_effect = [
            _make_execute_result(scalar_one_or_none=None),   # UserProfile
            _make_execute_result(scalars_first=plan),         # reload plan
        ]
        return session, plan

    def test_returns_201_with_plan(self):
        session, _ = self._setup()
        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "운동 루틴", date(2026, 6, 1), date(2026, 6, 3),
                _STUB_DAYS, _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            resp = client.post("/api/plans/generate", json=_VALID_BODY)
        assert resp.status_code == 201

    def test_response_source_is_ai(self):
        session, _ = self._setup()
        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "운동 루틴", date(2026, 6, 1), date(2026, 6, 3),
                _STUB_DAYS, _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            resp = client.post("/api/plans/generate", json=_VALID_BODY)
        data = resp.json()
        assert data["source"] == "ai"

    def test_response_contains_todos(self):
        session, _ = self._setup()
        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "운동 루틴", date(2026, 6, 1), date(2026, 6, 3),
                _STUB_DAYS, _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            resp = client.post("/api/plans/generate", json=_VALID_BODY)
        data = resp.json()
        assert "todos" in data
        assert len(data["todos"]) == 9  # 3 days × 3 todos

    def test_stub_called_with_correct_args(self):
        session, _ = self._setup()
        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "운동 루틴", date(2026, 6, 1), date(2026, 6, 3),
                _STUB_DAYS, _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            client.post("/api/plans/generate", json=_VALID_BODY)
        mock_inst.generate_plan.assert_called_once()
        call_kwargs = mock_inst.generate_plan.call_args.kwargs
        assert call_kwargs["description"] == "운동 루틴"
        assert call_kwargs["period_start"] == date(2026, 6, 1)
        assert call_kwargs["period_end"] == date(2026, 6, 3)
        assert call_kwargs["goal"] == "건강 유지"

    def test_with_user_profile(self):
        """UserProfile이 있으면 user_profile dict이 stub에 전달된다."""
        session = _make_session()
        profile = SimpleNamespace(
            nickname="테스터", occupation="개발자",
            hobbies=["독서"], interests=["AI"],
        )
        todos = [make_todo(id=i + 1) for i in range(3)]
        plan = make_plan(id=10, todos=todos)
        session.execute.side_effect = [
            _make_execute_result(scalar_one_or_none=profile),
            _make_execute_result(scalars_first=plan),
        ]

        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "AI Plan", date(2026, 6, 1), date(2026, 6, 3),
                _STUB_DAYS, _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            resp = client.post("/api/plans/generate", json=_VALID_BODY)

        assert resp.status_code == 201
        call_kwargs = mock_inst.generate_plan.call_args.kwargs
        assert call_kwargs["user_profile"] == {
            "nickname": "테스터",
            "occupation": "개발자",
            "hobbies": ["독서"],
            "interests": ["AI"],
        }

    def test_no_user_profile_passes_none(self):
        session, _ = self._setup()
        with patch("app.routers.plans.BedrockStubClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.generate_plan = AsyncMock(return_value=(
                "운동 루틴", date(2026, 6, 1), date(2026, 6, 3),
                _STUB_DAYS, _STUB_META,
            ))
            mock_cls.return_value = mock_inst
            client = _setup_client(session)
            client.post("/api/plans/generate", json=_VALID_BODY)
        call_kwargs = mock_inst.generate_plan.call_args.kwargs
        assert call_kwargs["user_profile"] is None
