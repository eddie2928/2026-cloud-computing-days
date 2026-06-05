"""
Integration tests for /api/plans — T04.
Covers 20 scenarios: migration/model, auth/권한, CRUD, AI generation, calendar.
"""
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Plan, PlanTodo, User


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


# ── A. Migration / Model Integrity ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_a1_plan_and_todo_tables_exist(client, db_session):
    """A-1: plans / plan_todos tables are created by alembic upgrade head."""
    await _login(client)
    resp = await client.post("/api/plans", json={
        "title": "테이블 확인",
        "period_start": "2027-01-01",
        "period_end": "2027-01-31",
    })
    assert resp.status_code == 201
    plan_id = resp.json()["id"]

    # Both tables must be queryable without error
    result = await db_session.execute(select(Plan).where(Plan.id == plan_id))
    assert result.scalars().first() is not None

    result2 = await db_session.execute(
        select(PlanTodo).where(PlanTodo.plan_id == plan_id)
    )
    assert result2.scalars().all() == []  # no todos yet — just confirm table exists


@pytest.mark.asyncio
async def test_a2_period_end_before_start_rejected_400(client):
    """A-2: POST /api/plans with period_end < period_start → 400."""
    await _login(client)
    resp = await client.post("/api/plans", json={
        "title": "잘못된 기간",
        "period_start": "2027-06-30",
        "period_end": "2027-06-01",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_a3_plan_todo_unique_constraint_violation(client, db_session):
    """A-3: inserting duplicate (plan_id, todo_date, sequence) raises IntegrityError."""
    await _login(client)
    plan_resp = await client.post("/api/plans", json={
        "title": "UNIQUE 제약 테스트",
        "period_start": "2027-02-01",
        "period_end": "2027-02-28",
    })
    assert plan_resp.status_code == 201
    plan_id = plan_resp.json()["id"]

    # First todo via API — OK
    r1 = await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2027-02-01",
        "sequence": 1,
        "content": "첫 할 일",
    })
    assert r1.status_code == 201

    # Direct DB insert of duplicate — must raise IntegrityError
    dup = PlanTodo(
        plan_id=plan_id,
        todo_date=date(2027, 2, 1),
        sequence=1,
        content="중복 할 일",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_a4_plan_delete_cascades_todos(client, db_session):
    """A-4: deleting a plan cascades delete to all its todos."""
    await _login(client)
    plan_resp = await client.post("/api/plans", json={
        "title": "CASCADE 테스트",
        "period_start": "2027-03-01",
        "period_end": "2027-03-10",
    })
    plan_id = plan_resp.json()["id"]

    for i in range(1, 4):
        await client.post(f"/api/plans/{plan_id}/todos", json={
            "todo_date": "2027-03-01",
            "sequence": i,
            "content": f"할 일 {i}",
        })

    del_resp = await client.delete(f"/api/plans/{plan_id}")
    assert del_resp.status_code == 204

    result = await db_session.execute(
        select(PlanTodo).where(PlanTodo.plan_id == plan_id)
    )
    assert result.scalars().all() == []


# ── B. Auth / 권한 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_b5_no_auth_get_plans_returns_401(client):
    """B-5: unauthenticated GET /api/plans → 401."""
    resp = await client.get("/api/plans")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_b6_other_user_plan_returns_404(client, db_session):
    """B-6: GET/PUT/DELETE on another user's plan → 404 (no existence leakage)."""
    await _login(client)

    # Create user 2 directly in DB (explicit ID to avoid PostgreSQL sequence conflict)
    user2 = User(id=90002, display_name="Test User 2 (b6)")
    db_session.add(user2)
    await db_session.flush()

    plan2 = Plan(
        user_id=user2.id,
        title="User2 전용 플랜",
        period_start=date(2027, 4, 1),
        period_end=date(2027, 4, 30),
        source="manual",
    )
    db_session.add(plan2)
    await db_session.flush()
    plan2_id = plan2.id
    await db_session.commit()

    # Accessing user2's plan as user1 must return 404
    assert (await client.get(f"/api/plans/{plan2_id}")).status_code == 404
    assert (await client.put(f"/api/plans/{plan2_id}", json={"title": "수정 시도"})).status_code == 404
    assert (await client.delete(f"/api/plans/{plan2_id}")).status_code == 404


@pytest.mark.asyncio
async def test_b7_other_user_todo_crud_returns_404(client, db_session):
    """B-7: todo CRUD on another user's plan → 404."""
    await _login(client)

    user3 = User(id=90003, display_name="Test User 3 (b7)")
    db_session.add(user3)
    await db_session.flush()

    plan3 = Plan(
        user_id=user3.id,
        title="User3 전용 플랜",
        period_start=date(2027, 5, 1),
        period_end=date(2027, 5, 31),
        source="manual",
    )
    db_session.add(plan3)
    await db_session.flush()
    plan3_id = plan3.id

    todo3 = PlanTodo(
        plan_id=plan3.id,
        todo_date=date(2027, 5, 1),
        sequence=1,
        content="User3 할 일",
    )
    db_session.add(todo3)
    await db_session.flush()
    todo3_id = todo3.id
    await db_session.commit()

    # POST todo on user3's plan → 404
    assert (await client.post(f"/api/plans/{plan3_id}/todos", json={
        "todo_date": "2027-05-01", "content": "침범 시도",
    })).status_code == 404

    # PUT todo on user3's plan → 404
    assert (await client.put(f"/api/plans/{plan3_id}/todos/{todo3_id}", json={
        "completed": True,
    })).status_code == 404

    # DELETE todo on user3's plan → 404
    assert (await client.delete(f"/api/plans/{plan3_id}/todos/{todo3_id}")).status_code == 404


# ── C. CRUD 정상 흐름 ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_c8_create_plan_and_get_same_data(client):
    """C-8: POST /api/plans → GET returns same data, progress=0."""
    await _login(client)
    create_resp = await client.post("/api/plans", json={
        "title": "6월 목표",
        "period_start": "2027-06-01",
        "period_end": "2027-06-30",
        "description_input": "공부 열심히",
    })
    assert create_resp.status_code == 201
    created = create_resp.json()
    plan_id = created["id"]

    get_resp = await client.get(f"/api/plans/{plan_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()

    assert fetched["id"] == plan_id
    assert fetched["title"] == "6월 목표"
    assert fetched["period_start"] == "2027-06-01"
    assert fetched["period_end"] == "2027-06-30"
    assert fetched["progress"] == 0.0
    assert fetched["todos"] == []


@pytest.mark.asyncio
async def test_c9_todo_complete_updates_progress_and_completed_at(client):
    """C-9: POST todo → PUT completed=true → progress recalculated, completed_at set."""
    await _login(client)
    plan_resp = await client.post("/api/plans", json={
        "title": "진척도 테스트",
        "period_start": "2027-07-01",
        "period_end": "2027-07-31",
    })
    plan_id = plan_resp.json()["id"]

    t1 = await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2027-07-01", "sequence": 1, "content": "할 일 1",
    })
    t2 = await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2027-07-01", "sequence": 2, "content": "할 일 2",
    })
    assert t1.status_code == 201
    assert t2.status_code == 201
    todo1_id = t1.json()["id"]

    # Toggle completed=True
    put_resp = await client.put(f"/api/plans/{plan_id}/todos/{todo1_id}", json={"completed": True})
    assert put_resp.status_code == 200
    assert put_resp.json()["completed"] is True
    assert put_resp.json()["completed_at"] is not None

    # Plan progress should be 0.5
    plan_get = await client.get(f"/api/plans/{plan_id}")
    assert plan_get.json()["progress"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_c10_all_todos_completed_progress_is_one(client):
    """C-10: all todos completed → progress=1.0."""
    await _login(client)
    plan_resp = await client.post("/api/plans", json={
        "title": "완료 테스트",
        "period_start": "2027-08-01",
        "period_end": "2027-08-31",
    })
    plan_id = plan_resp.json()["id"]

    todo_ids = []
    for i in range(1, 4):
        t = await client.post(f"/api/plans/{plan_id}/todos", json={
            "todo_date": "2027-08-01", "sequence": i, "content": f"할 일 {i}",
        })
        todo_ids.append(t.json()["id"])

    for tid in todo_ids:
        await client.put(f"/api/plans/{plan_id}/todos/{tid}", json={"completed": True})

    plan_get = await client.get(f"/api/plans/{plan_id}")
    assert plan_get.json()["progress"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_c11_update_plan_period_reflected_in_get(client):
    """C-11: PUT plan period/title → GET reflects the change."""
    await _login(client)
    create = await client.post("/api/plans", json={
        "title": "기간 변경 전",
        "period_start": "2027-09-01",
        "period_end": "2027-09-30",
    })
    plan_id = create.json()["id"]

    put_resp = await client.put(f"/api/plans/{plan_id}", json={
        "title": "기간 변경 후",
        "period_start": "2027-10-01",
        "period_end": "2027-10-31",
    })
    assert put_resp.status_code == 200

    get_resp = await client.get(f"/api/plans/{plan_id}")
    data = get_resp.json()
    assert data["title"] == "기간 변경 후"
    assert data["period_start"] == "2027-10-01"
    assert data["period_end"] == "2027-10-31"


@pytest.mark.asyncio
async def test_c12_delete_plan_returns_404_and_todos_gone(client, db_session):
    """C-12: DELETE plan → subsequent GET is 404, todos are removed from DB."""
    await _login(client)
    create = await client.post("/api/plans", json={
        "title": "삭제 대상 플랜",
        "period_start": "2027-11-01",
        "period_end": "2027-11-30",
    })
    plan_id = create.json()["id"]

    await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2027-11-01", "sequence": 1, "content": "삭제될 할 일",
    })

    del_resp = await client.delete(f"/api/plans/{plan_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/plans/{plan_id}")
    assert get_resp.status_code == 404

    result = await db_session.execute(
        select(PlanTodo).where(PlanTodo.plan_id == plan_id)
    )
    assert result.scalars().all() == []


# ── D. AI 생성 흐름 (stub) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_d13_generate_plan_source_ai_and_meta_stored(client, db_session, claude_mock):
    """D-13: POST /api/plans/generate → source='ai', ai_meta stored in DB."""
    from datetime import date as _date
    claude_mock.generate_plan.return_value = (
        "운동 루틴 AI",
        _date(2027, 12, 1),
        _date(2027, 12, 3),
        [
            {"date": _date(2027, 12, 1), "todos": ["아침 루틴"]},
            {"date": _date(2027, 12, 2), "todos": ["핵심 작업"]},
            {"date": _date(2027, 12, 3), "todos": ["마무리 회고"]},
        ],
        {"model_id": "test"},
    )
    await _login(client)
    resp = await client.post("/api/plans/generate", json={
        "description": "운동 루틴 만들기",
        "period_start": "2027-12-01",
        "period_end": "2027-12-03",
        "goal": "건강 유지",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "ai"
    assert len(data["todos"]) > 0

    # ai_meta is not in the response schema — verify via DB
    plan_id = data["id"]
    result = await db_session.execute(select(Plan).where(Plan.id == plan_id))
    db_plan = result.scalars().first()
    assert db_plan is not None
    assert db_plan.ai_meta is not None
    assert db_plan.ai_meta.get("model_id") == "test"


@pytest.mark.asyncio
async def test_d14_generate_plan_5_days_todos_cover_all_dates(client, claude_mock):
    """D-14: 5-day period → todos for each of the 5 dates."""
    from datetime import date as _date
    claude_mock.generate_plan.return_value = (
        "주간 AI 계획",
        _date(2028, 1, 1),
        _date(2028, 1, 5),
        [{"date": _date(2028, 1, d), "todos": ["할 일"]} for d in range(1, 6)],
        {"model_id": "test"},
    )
    await _login(client)
    resp = await client.post("/api/plans/generate", json={
        "description": "주간 계획 테스트",
        "period_start": "2028-01-01",
        "period_end": "2028-01-05",
        "goal": "5일 완주",
    })
    assert resp.status_code == 201
    todos = resp.json()["todos"]
    todo_dates = {t["todo_date"] for t in todos}
    expected = {"2028-01-01", "2028-01-02", "2028-01-03", "2028-01-04", "2028-01-05"}
    assert todo_dates == expected


@pytest.mark.asyncio
async def test_d15_generate_plan_empty_description_returns_422(client):
    """D-15: empty description → 422."""
    await _login(client)
    resp = await client.post("/api/plans/generate", json={
        "description": "",
        "period_start": "2028-02-01",
        "period_end": "2028-02-28",
        "goal": "목표",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_d16_generate_plan_period_end_before_start_returns_422(client):
    """D-16: period_end < period_start → 422."""
    await _login(client)
    resp = await client.post("/api/plans/generate", json={
        "description": "계획",
        "period_start": "2028-03-31",
        "period_end": "2028-03-01",
        "goal": "목표",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_d17_generate_plan_over_90_days_returns_422(client):
    """D-17: period > 90 days → 422."""
    await _login(client)
    resp = await client.post("/api/plans/generate", json={
        "description": "긴 계획",
        "period_start": "2028-04-01",
        "period_end": "2028-07-01",  # 91 days
        "goal": "목표",
    })
    assert resp.status_code == 422


# ── E. Calendar Query ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e18_calendar_returns_overlapping_plans_with_filtered_todos(client):
    """E-18: GET /api/plans/calendar returns overlapping plans; todos filtered to range."""
    await _login(client)
    plan_resp = await client.post("/api/plans", json={
        "title": "캘린더 오버랩 테스트",
        "period_start": "2028-05-15",
        "period_end": "2028-06-15",
    })
    plan_id = plan_resp.json()["id"]

    # Todo inside May
    await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2028-05-20", "sequence": 1, "content": "5월 할 일",
    })
    # Todo outside May (in June)
    await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2028-06-05", "sequence": 1, "content": "6월 할 일",
    })

    resp = await client.get("/api/plans/calendar?start=2028-05-01&end=2028-05-31")
    assert resp.status_code == 200
    data = resp.json()

    matched = next((p for p in data if p["id"] == plan_id), None)
    assert matched is not None, "plan overlapping May should appear"
    assert len(matched["todos"]) == 1
    assert matched["todos"][0]["todo_date"] == "2028-05-20"


@pytest.mark.asyncio
async def test_e19_calendar_plan_with_no_todos_in_range_returned_with_empty_todos(client):
    """E-19: plan within range but no todos in that range → returned with todos=[]."""
    await _login(client)
    plan_resp = await client.post("/api/plans", json={
        "title": "빈 todo 캘린더 테스트",
        "period_start": "2028-07-01",
        "period_end": "2028-08-31",
    })
    plan_id = plan_resp.json()["id"]

    # Todo is in August, but we query July
    await client.post(f"/api/plans/{plan_id}/todos", json={
        "todo_date": "2028-08-01", "sequence": 1, "content": "8월 할 일",
    })

    resp = await client.get("/api/plans/calendar?start=2028-07-01&end=2028-07-31")
    assert resp.status_code == 200
    data = resp.json()
    matched = next((p for p in data if p["id"] == plan_id), None)
    assert matched is not None, "plan spanning July-Aug should appear in July query"
    assert matched["todos"] == []


@pytest.mark.asyncio
async def test_e20_calendar_start_greater_than_end_returns_422(client):
    """E-20: start > end → 422."""
    await _login(client)
    resp = await client.get("/api/plans/calendar?start=2028-09-30&end=2028-09-01")
    assert resp.status_code == 422
