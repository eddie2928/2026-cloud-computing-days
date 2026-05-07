"""1B-5: Unit tests for gRPC client / addon gRPC integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from agentbox.proxy.addon import AgentBoxAddon


class _FakeResponse:
    def __init__(self, verdict="ALLOW", reasons=None, event_id="abc"):
        self.verdict = verdict
        self.reasons = reasons or []
        self.event_id = event_id


class _MockHTTPFlow:
    class _Req:
        method = "POST"
        pretty_host = "api.anthropic.com"
        pretty_url = "https://api.anthropic.com/v1/messages"
        headers = {}
        def get_text(self, strict=False):
            return '{"model":"claude-3-haiku","messages":[{"role":"user","content":"hello"}]}'
    request = _Req()
    response = None


@pytest.fixture
def addon(tmp_path):
    from agentbox import config as _cfg_mod
    _cfg_mod.cfg.DB_PATH = str(tmp_path / "test.db")
    _cfg_mod.cfg.GRPC_HOST = "ec2-test"
    return AgentBoxAddon()


@pytest.mark.asyncio
async def test_grpc_allow(addon):
    with patch("agentbox.grpc.client.inspect", return_value=_FakeResponse("ALLOW")) as mock_inspect:
        flow = _MockHTTPFlow()
        await addon._handle(flow)
        assert flow.response is None  # not blocked
        mock_inspect.assert_called_once()


@pytest.mark.asyncio
async def test_grpc_block(addon):
    reasons = ["내부 코드 유출 탐지"]
    with patch("agentbox.grpc.client.inspect",
               return_value=_FakeResponse("BLOCK", reasons)):
        flow = _MockHTTPFlow()
        await addon._handle(flow)
        assert flow.response is not None
        assert flow.response.status_code == 403
        assert b"Blocked" in flow.response.content


@pytest.mark.asyncio
async def test_grpc_rpc_error_safe_block(addon):
    """gRPC RpcError -> safe BLOCK."""
    err = grpc.RpcError()
    err.code = lambda: grpc.StatusCode.UNAVAILABLE
    err.details = lambda: "connection refused"
    with patch("agentbox.grpc.client.inspect", side_effect=err):
        flow = _MockHTTPFlow()
        await addon._handle(flow)
        assert flow.response is not None
        assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_grpc_timeout_safe_block(addon):
    """Timeout -> safe BLOCK."""
    with patch("agentbox.grpc.client.inspect", side_effect=Exception("deadline exceeded")):
        flow = _MockHTTPFlow()
        await addon._handle(flow)
        assert flow.response is not None
        assert flow.response.status_code == 403


@pytest.mark.asyncio
async def test_no_grpc_host_allow(tmp_path):
    """No GRPC_HOST configured -> ALLOW with warning (dev mode)."""
    from agentbox import config as _cfg_mod
    _cfg_mod.cfg.DB_PATH = str(tmp_path / "test.db")
    _cfg_mod.cfg.GRPC_HOST = ""
    addon = AgentBoxAddon()
    flow = _MockHTTPFlow()
    await addon._handle(flow)
    assert flow.response is None
