import pytest

_SUB = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-unique",
    "keys": {"p256dh": "p256dh_test_value", "auth": "auth_test_value"},
}

_SUB2 = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-unique",
    "keys": {"p256dh": "p256dh_updated", "auth": "auth_updated"},
}


@pytest.mark.asyncio
async def test_get_public_key(client):
    response = await client.get("/api/push/public-key")
    assert response.status_code == 200
    assert "public_key" in response.json()


@pytest.mark.asyncio
async def test_subscribe_requires_auth(client):
    response = await client.post("/api/push/subscribe", json=_SUB)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subscribe_creates_row(client, db_session):
    from app.models import PushSubscription
    from sqlalchemy import select

    await client.post("/api/login", json={"password": "inha-nxt"})
    response = await client.post("/api/push/subscribe", json=_SUB)
    assert response.status_code == 201

    result = await db_session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == _SUB["endpoint"])
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.user_id == 1
    assert row.p256dh == _SUB["keys"]["p256dh"]


@pytest.mark.asyncio
async def test_subscribe_upsert_no_duplicate(client, db_session):
    from app.models import PushSubscription
    from sqlalchemy import func, select

    await client.post("/api/login", json={"password": "inha-nxt"})
    await client.post("/api/push/subscribe", json=_SUB)
    response = await client.post("/api/push/subscribe", json=_SUB2)
    assert response.status_code == 201

    result = await db_session.execute(
        select(func.count()).where(PushSubscription.endpoint == _SUB["endpoint"])
    )
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_unsubscribe_deletes_row(client, db_session):
    from app.models import PushSubscription
    from sqlalchemy import select

    await client.post("/api/login", json={"password": "inha-nxt"})
    await client.post("/api/push/subscribe", json=_SUB)

    response = await client.request("DELETE", "/api/push/unsubscribe", json=_SUB)
    assert response.status_code == 204

    result = await db_session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == _SUB["endpoint"])
    )
    assert result.scalar_one_or_none() is None
