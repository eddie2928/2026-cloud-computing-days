"""
Integration tests for POST /api/plans/{plan_id}/todos/bulk_replace — T3.
"""
from datetime import date, timedelta

import pytest

from app.models import Plan, PlanTodo, User


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
TWO_DAYS_LATER = TODAY + timedelta(days=2)
TWO_DAYS_AGO = TODAY - timedelta(days=2)


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _create_plan(client, period_start: date, period_end: date) -> int:
    resp = await client.post("/api/plans", json={
        "title": "bulk_replace 테스트 플랜",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
    })
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_todo(client, plan_id: int, todo_date: date, content: str, seq: int = 1):
    resp = await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": todo_date.isoformat(),
        "sequence": seq,
        "content": content,
    })
    assert resp.status_code == 201
    return resp.json()


async def _bulk_replace(client, plan_id: int, contents: list[str]):
    return await client.post(
        f"/api/plans/{plan_id}/todos/bulk_replace",
        json={"contents": contents},
    )


@pytest.mark.asyncio
async def test_br1_all_future_period_todos_replaced(client):
    """BR-1: plan 기간 전체가 미래 → 모든 날짜에 새 todos 생성, completed=false."""
    await _login(client)
    plan_id = await _create_plan(client, TOMORROW, TWO_DAYS_LATER)

    resp = await _bulk_replace(client, plan_id, ["a", "b"])
    assert resp.status_code == 200

    data = resp.json()
    todos = data["todos"]

    tomorrow_todos = sorted(
        [t for t in todos if t["todo_date"] == TOMORROW.isoformat()],
        key=lambda t: t["sequence"],
    )
    day2_todos = sorted(
        [t for t in todos if t["todo_date"] == TWO_DAYS_LATER.isoformat()],
        key=lambda t: t["sequence"],
    )

    assert len(tomorrow_todos) == 2
    assert tomorrow_todos[0]["content"] == "a"
    assert tomorrow_todos[0]["completed"] is False
    assert tomorrow_todos[1]["content"] == "b"

    assert len(day2_todos) == 2
    assert day2_todos[0]["content"] == "a"
    assert day2_todos[1]["content"] == "b"


@pytest.mark.asyncio
async def test_br2_mixed_period_past_preserved_future_replaced(client):
    """BR-2: 과거+오늘+미래 혼합 기간 → 과거 행 불변, 오늘+미래 교체."""
    await _login(client)
    plan_id = await _create_plan(client, YESTERDAY, TOMORROW)

    # Pre-seed all three dates
    await _add_todo(client, plan_id, YESTERDAY, "어제 할 일", seq=1)
    await _add_todo(client, plan_id, TODAY, "오늘 기존 할 일", seq=1)
    await _add_todo(client, plan_id, TOMORROW, "내일 기존 할 일", seq=1)

    resp = await _bulk_replace(client, plan_id, ["x"])
    assert resp.status_code == 200

    todos = resp.json()["todos"]
    by_date: dict[str, list] = {}
    for t in todos:
        by_date.setdefault(t["todo_date"], []).append(t)

    # 과거(어제) 보존
    assert YESTERDAY.isoformat() in by_date
    assert len(by_date[YESTERDAY.isoformat()]) == 1
    assert by_date[YESTERDAY.isoformat()][0]["content"] == "어제 할 일"

    # 오늘 교체
    assert TODAY.isoformat() in by_date
    assert len(by_date[TODAY.isoformat()]) == 1
    assert by_date[TODAY.isoformat()][0]["content"] == "x"

    # 내일 교체
    assert TOMORROW.isoformat() in by_date
    assert len(by_date[TOMORROW.isoformat()]) == 1
    assert by_date[TOMORROW.isoformat()][0]["content"] == "x"


@pytest.mark.asyncio
async def test_br3_all_past_period_no_change(client):
    """BR-3: 기간 전체가 과거 → 변경 없이 현재 상태 반환."""
    await _login(client)
    plan_id = await _create_plan(client, TWO_DAYS_AGO, YESTERDAY)
    await _add_todo(client, plan_id, TWO_DAYS_AGO, "과거 할 일 1", seq=1)
    await _add_todo(client, plan_id, YESTERDAY, "과거 할 일 2", seq=1)

    resp = await _bulk_replace(client, plan_id, ["새로운 내용"])
    assert resp.status_code == 200

    todos = resp.json()["todos"]
    assert len(todos) == 2
    contents = {t["content"] for t in todos}
    assert "과거 할 일 1" in contents
    assert "과거 할 일 2" in contents
    assert "새로운 내용" not in contents


@pytest.mark.asyncio
async def test_br4_empty_contents_deletes_future_todos(client):
    """BR-4: 빈 contents → 오늘+미래 todos 전부 삭제, 과거 보존."""
    await _login(client)
    plan_id = await _create_plan(client, YESTERDAY, TOMORROW)
    await _add_todo(client, plan_id, YESTERDAY, "과거 보존", seq=1)
    await _add_todo(client, plan_id, TODAY, "오늘 삭제 대상", seq=1)
    await _add_todo(client, plan_id, TOMORROW, "미래 삭제 대상", seq=1)

    resp = await _bulk_replace(client, plan_id, [])
    assert resp.status_code == 200

    todos = resp.json()["todos"]
    assert len(todos) == 1
    assert todos[0]["content"] == "과거 보존"
    assert todos[0]["todo_date"] == YESTERDAY.isoformat()


@pytest.mark.asyncio
async def test_br5_other_user_plan_returns_404(client, db_session):
    """BR-5: 타 user의 plan에 bulk_replace → 404."""
    await _login(client)

    user2 = User(id=91001, display_name="BR Test User2")
    db_session.add(user2)
    await db_session.flush()

    plan2 = Plan(
        user_id=user2.id,
        title="타 유저 플랜",
        period_start=TOMORROW,
        period_end=TWO_DAYS_LATER,
        source="manual",
    )
    db_session.add(plan2)
    await db_session.flush()
    plan2_id = plan2.id
    await db_session.commit()

    resp = await _bulk_replace(client, plan2_id, ["침범 시도"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_br6_content_too_long_returns_422(client):
    """BR-6: content > 500자 → 422."""
    await _login(client)
    plan_id = await _create_plan(client, TOMORROW, TWO_DAYS_LATER)

    long_content = "x" * 501
    resp = await _bulk_replace(client, plan_id, [long_content])
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_br6b_too_many_contents_returns_422(client):
    """BR-6b: list > 50 items → 422."""
    await _login(client)
    plan_id = await _create_plan(client, TOMORROW, TWO_DAYS_LATER)

    resp = await _bulk_replace(client, plan_id, ["item"] * 51)
    assert resp.status_code == 422
