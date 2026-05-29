"""
@reusable
@scope project-local
@description SQLAlchemy 모델 컬럼/제약 존재 확인 패턴 + Pydantic 스키마 default값/optional 필드 검증 패턴
@usage app.models, app.schemas import 경로를 실제 프로젝트 모델/스키마에 맞게 교체.
       테이블명, 컬럼명, 제약 이름은 해당 모델에 맞게 수정.
@origin proj_days / T01 Plan+PlanTodo 모델+스키마 구현
@created 2026-05-29
"""
import os
import pytest
from datetime import date, datetime

os.environ.setdefault("APP_PASSWORD", "test")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")

from app.models import Plan, PlanTodo
from app.schemas import (
    PlanCreate,
    PlanGenerateInput,
    PlanOut,
    PlanTodoCreate,
    PlanTodoOut,
    PlanTodoUpdate,
    PlanUpdate,
    PlanWithTodosOut,
)


# ── 모델 클래스 구조 확인 ──────────────────────────────────────────

class TestPlanModelStructure:
    def test_plan_tablename(self):
        assert Plan.__tablename__ == "plans"

    def test_plan_todo_tablename(self):
        assert PlanTodo.__tablename__ == "plan_todos"

    def test_plan_has_required_columns(self):
        cols = {c.key for c in Plan.__table__.columns}
        for col in ("id", "user_id", "title", "period_start", "period_end", "source",
                    "created_at", "updated_at"):
            assert col in cols, f"Missing column: {col}"

    def test_plan_has_optional_columns(self):
        cols = {c.key for c in Plan.__table__.columns}
        for col in ("description_input", "goal_input", "ai_meta"):
            assert col in cols, f"Missing optional column: {col}"

    def test_plan_todo_has_required_columns(self):
        cols = {c.key for c in PlanTodo.__table__.columns}
        for col in ("id", "plan_id", "todo_date", "sequence", "content", "completed", "created_at"):
            assert col in cols, f"Missing column: {col}"

    def test_plan_todo_has_completed_at(self):
        cols = {c.key for c in PlanTodo.__table__.columns}
        assert "completed_at" in cols

    def test_plan_source_server_default(self):
        col = Plan.__table__.c["source"]
        assert col.server_default is not None

    def test_plan_todo_completed_server_default(self):
        col = PlanTodo.__table__.c["completed"]
        assert col.server_default is not None

    def test_plan_has_check_constraint(self):
        constraint_names = {c.name for c in Plan.__table__.constraints}
        assert "ck_plan_period" in constraint_names

    def test_plan_todo_unique_constraint(self):
        from sqlalchemy import UniqueConstraint as UC
        constraint_cols = set()
        for c in PlanTodo.__table__.constraints:
            if isinstance(c, UC):
                constraint_cols.update(col.name for col in c.columns)
        assert {"plan_id", "todo_date", "sequence"}.issubset(constraint_cols)


# ── PlanTodoCreate ────────────────────────────────────────────────

def test_plan_todo_create_required_fields():
    t = PlanTodoCreate(todo_date=date(2026, 6, 1), sequence=1, content="운동하기")
    assert t.todo_date == date(2026, 6, 1)
    assert t.sequence == 1
    assert t.content == "운동하기"


def test_plan_todo_create_missing_content():
    with pytest.raises(Exception):
        PlanTodoCreate(todo_date=date(2026, 6, 1), sequence=1)


# ── PlanTodoUpdate ────────────────────────────────────────────────

def test_plan_todo_update_all_optional():
    u = PlanTodoUpdate()
    assert u.sequence is None
    assert u.content is None
    assert u.completed is None


def test_plan_todo_update_partial():
    u = PlanTodoUpdate(completed=True)
    assert u.completed is True
    assert u.sequence is None


# ── PlanTodoOut ───────────────────────────────────────────────────

def test_plan_todo_out_fields():
    t = PlanTodoOut(
        id=1,
        plan_id=10,
        todo_date=date(2026, 6, 1),
        sequence=1,
        content="독서",
        completed=False,
        completed_at=None,
    )
    assert t.id == 1
    assert t.completed is False
    assert t.completed_at is None


def test_plan_todo_out_from_orm_compatible():
    t = PlanTodoOut.model_validate({
        "id": 2,
        "plan_id": 5,
        "todo_date": date(2026, 6, 2),
        "sequence": 2,
        "content": "글쓰기",
        "completed": True,
        "completed_at": datetime(2026, 6, 2, 10, 0, 0),
    })
    assert t.completed is True


# ── PlanCreate ────────────────────────────────────────────────────

def test_plan_create_required():
    p = PlanCreate(
        title="6월 목표",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
    )
    assert p.title == "6월 목표"
    assert p.source == "manual"
    assert p.description_input is None
    assert p.goal_input is None


def test_plan_create_with_optional():
    p = PlanCreate(
        title="AI 플랜",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        description_input="매일 공부",
        goal_input="자격증 취득",
        source="ai",
    )
    assert p.source == "ai"
    assert p.goal_input == "자격증 취득"


def test_plan_create_missing_title():
    with pytest.raises(Exception):
        PlanCreate(period_start=date(2026, 6, 1), period_end=date(2026, 6, 30))


# ── PlanUpdate ────────────────────────────────────────────────────

def test_plan_update_all_optional():
    u = PlanUpdate()
    assert u.title is None
    assert u.period_start is None


def test_plan_update_partial():
    u = PlanUpdate(title="수정된 목표")
    assert u.title == "수정된 목표"
    assert u.period_end is None


# ── PlanOut ───────────────────────────────────────────────────────

def test_plan_out_has_progress_field():
    p = PlanOut(
        id=1,
        user_id=1,
        title="목표",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        source="manual",
        created_at=datetime(2026, 6, 1, 0, 0, 0),
        progress=0.5,
    )
    assert p.progress == 0.5


def test_plan_out_progress_default():
    p = PlanOut(
        id=1,
        user_id=1,
        title="목표",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        source="manual",
        created_at=datetime(2026, 6, 1, 0, 0, 0),
    )
    assert p.progress == 0.0


# ── PlanWithTodosOut ──────────────────────────────────────────────

def test_plan_with_todos_out_extends_plan_out():
    p = PlanWithTodosOut(
        id=1,
        user_id=1,
        title="목표",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        source="manual",
        created_at=datetime(2026, 6, 1, 0, 0, 0),
        todos=[],
    )
    assert p.todos == []
    assert hasattr(p, "progress")


def test_plan_with_todos_out_with_todos():
    todo = PlanTodoOut(
        id=1, plan_id=1,
        todo_date=date(2026, 6, 1),
        sequence=1,
        content="수영",
        completed=False,
    )
    p = PlanWithTodosOut(
        id=1, user_id=1, title="목표",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        source="manual",
        created_at=datetime(2026, 6, 1),
        todos=[todo],
    )
    assert len(p.todos) == 1
    assert p.todos[0].content == "수영"


# ── PlanGenerateInput ─────────────────────────────────────────────

def test_plan_generate_input_fields():
    g = PlanGenerateInput(
        description="체력 증진",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        goal="마라톤 완주",
    )
    assert g.description == "체력 증진"
    assert g.goal == "마라톤 완주"


def test_plan_generate_input_missing_goal():
    with pytest.raises(Exception):
        PlanGenerateInput(
            description="체력 증진",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
        )
