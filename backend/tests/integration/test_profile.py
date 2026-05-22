import pytest


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


_PROFILE_PAYLOAD = {
    "nickname": "수진",
    "gender": "female",
    "age": 25,
    "occupation": "개발자",
    "hobbies": ["독서", "요가"],
    "interests": ["커리어", "건강"],
    "notification_time": None,
}


@pytest.mark.asyncio
async def test_get_profile_not_found(client, bedrock_mock):
    await _login(client)
    resp = await client.get("/api/profile")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_profile_create_and_retrieve(client, bedrock_mock):
    await _login(client)
    resp = await client.put("/api/profile", json=_PROFILE_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "수진"
    assert data["gender"] == "female"
    assert data["age"] == 25
    assert "독서" in data["hobbies"]
    assert "커리어" in data["interests"]

    get_resp = await client.get("/api/profile")
    assert get_resp.status_code == 200
    assert get_resp.json()["nickname"] == "수진"


@pytest.mark.asyncio
async def test_put_profile_update(client, bedrock_mock):
    await _login(client)
    await client.put("/api/profile", json=_PROFILE_PAYLOAD)

    updated = {**_PROFILE_PAYLOAD, "nickname": "민준", "age": 30}
    resp = await client.put("/api/profile", json=updated)
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "민준"
    assert resp.json()["age"] == 30


@pytest.mark.asyncio
async def test_put_profile_unauthenticated(client, bedrock_mock):
    resp = await client.put("/api/profile", json=_PROFILE_PAYLOAD)
    assert resp.status_code == 401
