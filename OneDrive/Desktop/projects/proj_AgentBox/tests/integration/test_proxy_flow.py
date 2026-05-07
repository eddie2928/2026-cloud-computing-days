from unittest.mock import MagicMock, patch
import pytest
import grpc

from agentbox.proxy.addon import AgentBoxAddon


def _make_flow(host="api.anthropic.com"):
    flow = MagicMock()
    flow.request.pretty_host = host
    flow.request.pretty_url = f"https://{host}/v1/messages"
    flow.request.method = "POST"
    flow.request.headers = {"content-type": "application/json"}
    flow.request.get_text.return_value = '{"model":"claude-3-5-sonnet"}'
    flow.response = None
    return flow


def _mock_response(verdict="ALLOW", reasons=None):
    resp = MagicMock()
    resp.verdict = verdict
    resp.reasons = reasons or []
    resp.event_id = "test-event-id"
    return resp


@pytest.mark.asyncio
async def test_allow_flow():
    addon = AgentBoxAddon()
    flow = _make_flow()

    with patch("agentbox.grpc.client.inspect", return_value=_mock_response("ALLOW")), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is None


@pytest.mark.asyncio
async def test_block_flow():
    addon = AgentBoxAddon()
    flow = _make_flow()

    with patch("agentbox.grpc.client.inspect",
               return_value=_mock_response("BLOCK", ["내부 코드 유출"])), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403


class _FakeRpcError(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.UNAVAILABLE
    def details(self):
        return "server down"


@pytest.mark.asyncio
async def test_grpc_unavailable_blocks():
    """gRPC connection failure must result in safe BLOCK."""
    addon = AgentBoxAddon()
    flow = _make_flow()

    with patch("agentbox.grpc.client.inspect", side_effect=_FakeRpcError()), \
         patch("agentbox.config.cfg.GRPC_HOST", "localhost"):
        await addon._handle(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403
