import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import grpc

from agentbox.proxy.addon import AgentBoxAddon
from agentbox.api.hitl import HITLQueue


def _make_flow(host="api.anthropic.com", method="POST", body=b'{"model":"test"}'):
    flow = MagicMock()
    flow.request.pretty_host = host
    flow.request.pretty_url = f"https://{host}/v1/messages"
    flow.request.method = method
    flow.request.headers = {"content-type": "application/json"}
    flow.request.get_text.return_value = body.decode()
    flow.response = None
    return flow


@pytest.mark.asyncio
async def test_non_target_passthrough():
    addon = AgentBoxAddon()
    flow = _make_flow(host="example.com")
    await addon.request(flow)
    assert flow.response is None


@pytest.mark.asyncio
async def test_allow_verdict_no_response():
    addon = AgentBoxAddon()
    flow = _make_flow()

    mock_resp = MagicMock()
    mock_resp.verdict = "ALLOW"
    mock_resp.reasons = []
    mock_resp.event_id = "abc123"

    with patch("agentbox.grpc.client.inspect", return_value=mock_resp), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is None


@pytest.mark.asyncio
async def test_block_verdict_sets_403():
    addon = AgentBoxAddon()
    flow = _make_flow()

    mock_resp = MagicMock()
    mock_resp.verdict = "BLOCK"
    mock_resp.reasons = ["내부 코드 유출 탐지"]
    mock_resp.event_id = "abc123"

    with patch("agentbox.grpc.client.inspect", return_value=mock_resp), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403


class _FakeRpcError(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.UNAVAILABLE
    def details(self):
        return "connection refused"


@pytest.mark.asyncio
async def test_grpc_error_causes_block():
    addon = AgentBoxAddon()
    flow = _make_flow()

    with patch("agentbox.grpc.client.inspect", side_effect=_FakeRpcError()), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_unexpected_exception_causes_block():
    addon = AgentBoxAddon()
    flow = _make_flow()

    with patch("agentbox.grpc.client.inspect", side_effect=RuntimeError("boom")), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_no_grpc_host_allows():
    """When GRPC_HOST is empty (dev mode), traffic is allowed through."""
    addon = AgentBoxAddon()
    flow = _make_flow()

    with patch("agentbox.config.cfg.GRPC_HOST", ""):
        await addon._handle(flow)

    assert flow.response is None
