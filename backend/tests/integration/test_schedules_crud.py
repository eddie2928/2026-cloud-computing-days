"""Integration tests for schedule CRUD API (todo #F-1)."""
from datetime import date

import pytest
from sqlalchemy import select

from app.models import UserSchedule


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_schedule(client, db_session):
    await _login(client)
    resp = await client.post("/api/schedules", json={
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "situation": "여름 방학",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["situation"] == "여름 방학"
    assert data["period_start"] == "2026-08-01"
    assert data["id"] is not None

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.situation == "여름 방학")
    )
    row = result.scalars().first()
    assert row is not None
    assert row.period_start == date(2026, 8, 1)


@pytest.mark.asyncio
async def test_get_schedules_month_filter(client, db_session):
    await _login(client)
    # Create a schedule spanning Aug-Sep
    await client.post("/api/schedules", json={
        "period_start": "2026-09-15",
        "period_end": "2026-10-15",
        "situation": "월 경계 일정",
    })

    # Request Oct — should be included
    resp_oct = await client.get("/api/schedules?month=2026-10")
    assert resp_oct.status_code == 200
    situations = [s["situation"] for s in resp_oct.json()]
    assert "월 경계 일정" in situations

    # Request Aug — should NOT be included
    resp_aug = await client.get("/api/schedules?month=2026-08")
    assert resp_aug.status_code == 200
    situations_aug = [s["situation"] for s in resp_aug.json()]
    assert "월 경계 일정" not in situations_aug


@pytest.mark.asyncio
async def test_update_schedule(client):
    await _login(client)
    create = await client.post("/api/schedules", json={
        "period_start": "2026-11-01",
        "period_end": "2026-11-30",
        "situation": "수정 전",
    })
    assert create.status_code == 201
    schedule_id = create.json()["id"]

    patch_resp = await client.patch(f"/api/schedules/{schedule_id}", json={
        "situation": "수정 후",
        "period_end": "2026-11-15",
    })
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["situation"] == "수정 후"
    assert data["period_end"] == "2026-11-15"


@pytest.mark.asyncio
async def test_delete_schedule(client, db_session):
    await _login(client)
    create = await client.post("/api/schedules", json={
        "period_start": "2026-12-01",
        "period_end": "2026-12-31",
        "situation": "삭제 대상",
    })
    assert create.status_code == 201
    schedule_id = create.json()["id"]

    del_resp = await client.delete(f"/api/schedules/{schedule_id}")
    assert del_resp.status_code == 204

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.id == schedule_id)
    )
    assert result.scalars().first() is None


@pytest.mark.asyncio
async def test_delete_other_user_schedule_returns_404(client):
    """Attempting to delete a non-existent schedule returns 404."""
    await _login(client)
    resp = await client.delete("/api/schedules/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_other_user_schedule_returns_404(client):
    """Attempting to update a non-existent schedule returns 404."""
    await _login(client)
    resp = await client.patch("/api/schedules/999999", json={"situation": "시도"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_schedule_by_id(client):
    await _login(client)
    create = await client.post("/api/schedules", json={
        "period_start": "2027-03-01",
        "period_end": "2027-03-31",
        "situation": "단건 조회 테스트",
    })
    assert create.status_code == 201
    schedule_id = create.json()["id"]

    resp = await client.get(f"/api/schedules/{schedule_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == schedule_id
    assert data["situation"] == "단건 조회 테스트"
    assert data["period_start"] == "2027-03-01"


@pytest.mark.asyncio
async def test_get_schedule_not_found(client):
    await _login(client)
    resp = await client.get("/api/schedules/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_schedule_returns_409(client):
    await _login(client)
    payload = {"period_start": "2027-01-01", "period_end": "2027-01-31", "situation": "중복 테스트"}
    first = await client.post("/api/schedules", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/schedules", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_schedule_time_round_trip(client):
    """POST에 시간 포함 → GET에서 시간 그대로 반환 (A6)."""
    await _login(client)
    create = await client.post("/api/schedules", json={
        "period_start": "2027-06-01",
        "period_end": "2027-06-01",
        "start_time": "14:00:00",
        "end_time": "16:00:00",
        "situation": "시간 왕복 테스트",
    })
    assert create.status_code == 201
    data = create.json()
    assert data["start_time"] == "14:00:00"
    assert data["end_time"] == "16:00:00"

    schedule_id = data["id"]
    get_resp = await client.get(f"/api/schedules/{schedule_id}")
    assert get_resp.status_code == 200
    got = get_resp.json()
    assert got["start_time"] == "14:00:00"
    assert got["end_time"] == "16:00:00"


@pytest.mark.asyncio
async def test_schedule_time_patch(client):
    """PATCH으로 시간 변경이 DB에 반영됨 (A6)."""
    await _login(client)
    create = await client.post("/api/schedules", json={
        "period_start": "2027-07-01",
        "period_end": "2027-07-01",
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "situation": "시간 수정 테스트",
    })
    assert create.status_code == 201
    schedule_id = create.json()["id"]

    patch_resp = await client.patch(f"/api/schedules/{schedule_id}", json={
        "start_time": "15:00:00",
        "end_time": "17:30:00",
    })
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["start_time"] == "15:00:00"
    assert data["end_time"] == "17:30:00"


@pytest.mark.asyncio
async def test_schedule_without_time_returns_null(client):
    """시간 없이 생성 시 start_time/end_time=null (하위호환, A6)."""
    await _login(client)
    create = await client.post("/api/schedules", json={
        "period_start": "2027-08-01",
        "period_end": "2027-08-31",
        "situation": "시간 없는 일정",
    })
    assert create.status_code == 201
    data = create.json()
    assert data["start_time"] is None
    assert data["end_time"] is None
