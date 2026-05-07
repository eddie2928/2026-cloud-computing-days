"""1C-8: Integration test - gRPC Inspector with regex block + DynamoDB mock."""
import json
from concurrent import futures
from unittest.mock import MagicMock, patch

import grpc
import pytest

from agentbox.grpc import inspect_pb2, inspect_pb2_grpc
from ec2.grpc_server.server import InspectorServicer


@pytest.fixture
def grpc_server():
    port = 50098
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    inspect_pb2_grpc.add_InspectorServicer_to_server(InspectorServicer(), server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    yield port
    server.stop(grace=0)


def _stub(port: int):
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    return inspect_pb2_grpc.InspectorStub(channel), channel


@patch("ec2.grpc_server.server._record_event")
@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "")
def test_regex_block_aws_key(mock_record, grpc_server):
    """AWS access key in prompt -> BLOCK from regex without Bedrock call."""
    stub, ch = _stub(grpc_server)
    resp = stub.Inspect(inspect_pb2.InspectRequest(
        user_id="dev",
        prompt="Use AKIAIOSFODNN7EXAMPLE for the AWS call",
        model="",
    ), timeout=5)
    ch.close()
    assert resp.verdict == "BLOCK"
    assert any("기밀값" in r for r in resp.reasons)
    mock_record.assert_called_once()


@patch("ec2.grpc_server.server._record_event")
@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "")
def test_clean_prompt_allow(mock_record, grpc_server):
    """Clean prompt with no Bedrock -> ALLOW."""
    stub, ch = _stub(grpc_server)
    resp = stub.Inspect(inspect_pb2.InspectRequest(
        user_id="dev",
        prompt="Explain binary search algorithm.",
        model="",
    ), timeout=5)
    ch.close()
    assert resp.verdict == "ALLOW"


@patch("ec2.grpc_server.server._record_event")
@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "")
def test_prompt_too_long_block(mock_record, grpc_server):
    """Prompt exceeding PROMPT_MAX_CHARS -> BLOCK."""
    with patch("ec2.grpc_server.server._PROMPT_MAX_CHARS", 10):
        stub, ch = _stub(grpc_server)
        resp = stub.Inspect(inspect_pb2.InspectRequest(
            user_id="dev",
            prompt="A" * 20,
            model="",
        ), timeout=5)
        ch.close()
    assert resp.verdict == "BLOCK"
    assert any("길이" in r for r in resp.reasons)
