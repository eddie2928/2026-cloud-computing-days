"""2A-8: Unit tests for Bedrock client adapter using botocore.stub."""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_streaming_response(verdict: str, reasons: list):
    """Build a mock Bedrock invoke_agent streaming response."""
    body_text = json.dumps({"verdict": verdict, "reasons": reasons})

    class _Stream:
        def __iter__(self):
            yield {"chunk": {"bytes": body_text.encode()}}

    return {"completion": _Stream()}


@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "test-agent-id")
@patch("ec2.grpc_server.server._bedrock_runtime")
def test_invoke_agent_allow(mock_bedrock):
    mock_bedrock.invoke_agent.return_value = _make_streaming_response("ALLOW", [])
    from ec2.grpc_server.server import _invoke_bedrock_agent
    verdict, reasons = _invoke_bedrock_agent("Hello world", "sess-1")
    assert verdict == "ALLOW"
    assert reasons == []


@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "test-agent-id")
@patch("ec2.grpc_server.server._bedrock_runtime")
def test_invoke_agent_block(mock_bedrock):
    mock_bedrock.invoke_agent.return_value = _make_streaming_response(
        "BLOCK", ["내부 코드 유출 탐지"]
    )
    from ec2.grpc_server.server import _invoke_bedrock_agent
    verdict, reasons = _invoke_bedrock_agent("def secret_func():", "sess-2")
    assert verdict == "BLOCK"
    assert "내부 코드 유출 탐지" in reasons


@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "test-agent-id")
@patch("ec2.grpc_server.server._bedrock_runtime")
def test_invoke_agent_parse_failure_fallback(mock_bedrock):
    """If Bedrock response is not JSON -> BLOCK fallback."""
    class _BadStream:
        def __iter__(self):
            yield {"chunk": {"bytes": b"NOT JSON"}}

    mock_bedrock.invoke_agent.return_value = {"completion": _BadStream()}
    from ec2.grpc_server.server import _invoke_bedrock_agent
    verdict, _ = _invoke_bedrock_agent("test", "sess-3")
    assert verdict == "BLOCK"


def test_cost_guard_token_cap():
    """When daily tokens exceed cap -> regex-only mode (no Bedrock call)."""
    with patch("ec2.grpc_server.server._daily_token_count", return_value=200000), \
         patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "agent-id"), \
         patch("ec2.grpc_server.server._record_event"), \
         patch("ec2.grpc_server.server._invoke_bedrock_agent") as mock_invoke:
        from concurrent import futures
        import grpc
        from agentbox.grpc import inspect_pb2, inspect_pb2_grpc
        from ec2.grpc_server.server import InspectorServicer

        # With token cap exceeded and no regex match -> ALLOW without Bedrock
        servicer = InspectorServicer()
        mock_ctx = MagicMock()
        resp = servicer.Inspect(
            inspect_pb2.InspectRequest(user_id="u", prompt="clean prompt", model=""),
            mock_ctx,
        )
        mock_invoke.assert_not_called()
        assert resp.verdict == "ALLOW"
