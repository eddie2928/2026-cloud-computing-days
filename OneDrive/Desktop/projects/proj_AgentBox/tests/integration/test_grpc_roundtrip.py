"""1B-6: Integration test - addon -> local mock gRPC server -> verdict round-trip."""
import threading
from concurrent import futures

import grpc
import pytest

from agentbox.grpc import inspect_pb2, inspect_pb2_grpc


class _MockInspectorServicer(inspect_pb2_grpc.InspectorServicer):
    def __init__(self, verdict="ALLOW", reasons=None):
        self.verdict = verdict
        self.reasons = reasons or []

    def Inspect(self, request, context):
        return inspect_pb2.InspectResponse(
            verdict=self.verdict,
            reasons=self.reasons,
            event_id="test-event-1",
        )


def _start_mock_server(port: int, servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    inspect_pb2_grpc.add_InspectorServicer_to_server(servicer, server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    return server


@pytest.fixture
def mock_grpc_server():
    port = 50099
    servicer = _MockInspectorServicer("ALLOW")
    server = _start_mock_server(port, servicer)
    yield port, servicer
    server.stop(grace=0)


def test_inspect_allow_roundtrip(mock_grpc_server):
    port, servicer = mock_grpc_server
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    stub = inspect_pb2_grpc.InspectorStub(channel)
    resp = stub.Inspect(inspect_pb2.InspectRequest(
        user_id="dev", prompt="Hello world", model="claude-3-haiku"
    ), timeout=5)
    assert resp.verdict == "ALLOW"
    assert resp.event_id == "test-event-1"
    channel.close()


def test_inspect_block_roundtrip(mock_grpc_server):
    port, servicer = mock_grpc_server
    servicer.verdict = "BLOCK"
    servicer.reasons = ["내부 코드 유출 탐지"]
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    stub = inspect_pb2_grpc.InspectorStub(channel)
    resp = stub.Inspect(inspect_pb2.InspectRequest(
        user_id="dev", prompt="SECRET_KEY=abc123", model=""
    ), timeout=5)
    assert resp.verdict == "BLOCK"
    assert "내부 코드 유출 탐지" in resp.reasons
    channel.close()


@pytest.mark.asyncio
async def test_addon_grpc_roundtrip(mock_grpc_server, tmp_path):
    """End-to-end: addon uses mock gRPC server, BLOCK verdict -> 403."""
    port, servicer = mock_grpc_server
    servicer.verdict = "BLOCK"
    servicer.reasons = ["테스트 차단"]

    from agentbox import config as _cfg_mod
    _cfg_mod.cfg.GRPC_HOST = "127.0.0.1"
    _cfg_mod.cfg.GRPC_PORT = port
    _cfg_mod.cfg.GRPC_CA_CERT = ""
    _cfg_mod.cfg.DB_PATH = str(tmp_path / "test.db")

    # Clear channel pool so new host:port is picked up
    import agentbox.grpc.client as _client
    _client._pool.clear()
    _client._pool_idx = 0

    from agentbox.proxy.addon import AgentBoxAddon
    addon = AgentBoxAddon()

    class _Flow:
        class _Req:
            method = "POST"
            pretty_host = "api.anthropic.com"
            pretty_url = "https://api.anthropic.com/v1/messages"
            headers = {}
            def get_text(self, strict=False):
                return '{"model":"claude-3-haiku","messages":[{"role":"user","content":"SECRET"}]}'
        request = _Req()
        response = None

    flow = _Flow()
    await addon._handle(flow)
    assert flow.response is not None
    assert flow.response.status_code == 403
