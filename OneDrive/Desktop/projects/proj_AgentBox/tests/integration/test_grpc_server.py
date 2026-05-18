"""Integration test - gRPC Inspector with regex block + DynamoDB mock.

Note: These tests call InspectorServicer.Inspect() directly to avoid
gRPC port binding, which fails in Windows Store Python (AppContainer).
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from agentbox.grpc import inspect_pb2, inspect_pb2_grpc
from ec2.grpc_server.server import InspectorServicer, serve


def test_serve_raises_when_cert_missing(tmp_path):
    os.environ["GRPC_CERTS_DIR"] = str(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="server cert missing"):
            serve()
    finally:
        del os.environ["GRPC_CERTS_DIR"]


@pytest.fixture
def servicer():
    return InspectorServicer()


def _context():
    return MagicMock()


@patch("ec2.grpc_server.server._record_event")
@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "")
def test_regex_block_aws_key(mock_record, servicer):
    """AWS access key in prompt -> BLOCK from regex without Bedrock call."""
    req = inspect_pb2.InspectRequest(
        user_id="dev",
        prompt="Use AKIAIOSFODNN7EXAMPLE for the AWS call",
        model="",
    )
    resp = servicer.Inspect(req, _context())
    assert resp.verdict == "BLOCK"
    assert any("기밀값" in r for r in resp.reasons)
    mock_record.assert_called_once()


@patch("ec2.grpc_server.server._record_event")
@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "")
def test_clean_prompt_allow(mock_record, servicer):
    """Clean prompt with no Bedrock -> ALLOW."""
    req = inspect_pb2.InspectRequest(
        user_id="dev",
        prompt="Explain binary search algorithm.",
        model="",
    )
    resp = servicer.Inspect(req, _context())
    assert resp.verdict == "ALLOW"


@patch("ec2.grpc_server.server._record_event")
@patch("ec2.grpc_server.server._BEDROCK_AGENT_ID", "")
def test_prompt_too_long_block(mock_record, servicer):
    """Prompt exceeding PROMPT_MAX_CHARS -> BLOCK."""
    with patch("ec2.grpc_server.server._PROMPT_MAX_CHARS", 10):
        req = inspect_pb2.InspectRequest(
            user_id="dev",
            prompt="A" * 20,
            model="",
        )
        resp = servicer.Inspect(req, _context())
    assert resp.verdict == "BLOCK"
    assert any("길이" in r for r in resp.reasons)
