"""Unit tests verifying that grpc Inspect calls MCP cleanup after verdict."""
import os
import pytest
import responses as resp_lib
from unittest.mock import MagicMock, patch


MCP_URL = "http://mcp-test:8080"
ADMIN_TOKEN = "grpc-test-token"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", MCP_URL)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("PROJECT_NAME", "agentbox")
    monkeypatch.setenv("BEDROCK_AGENT_ID", "test-agent-id")
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", "test-alias-id")


@resp_lib.activate
def test_inspect_calls_mcp_cleanup(monkeypatch):
    import importlib
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    # Register the cleanup endpoint
    resp_lib.add(
        resp_lib.DELETE,
        f"{MCP_URL}/mcp/cleanup/",
        match_querystring=False,
        status=200,
        json={"deleted": 0},
    )

    # Mock Bedrock agent call
    with patch.object(srv, "_invoke_bedrock_agent", return_value=("ALLOW", [])):
        with patch.object(srv, "_record_event"):
            with patch.object(srv, "_daily_token_count", return_value=0):
                servicer = srv.InspectorServicer()
                request = MagicMock()
                request.prompt = "is this code safe?"
                request.user_id = "test-user"
                context = MagicMock()
                result = servicer.Inspect(request, context)

    assert result.verdict == "ALLOW"
    # Verify cleanup was called
    delete_calls = [c for c in resp_lib.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 1
    assert "/mcp/cleanup/" in delete_calls[0].request.url


@resp_lib.activate
def test_cleanup_auth_header(monkeypatch):
    import importlib
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    resp_lib.add(
        resp_lib.DELETE,
        f"{MCP_URL}/mcp/cleanup/",
        match_querystring=False,
        status=200,
        json={"deleted": 0},
    )

    with patch.object(srv, "_invoke_bedrock_agent", return_value=("BLOCK", ["test"])):
        with patch.object(srv, "_record_event"):
            with patch.object(srv, "_daily_token_count", return_value=0):
                servicer = srv.InspectorServicer()
                request = MagicMock()
                request.prompt = "bad prompt"
                request.user_id = "u"
                result = servicer.Inspect(request, MagicMock())

    delete_calls = [c for c in resp_lib.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 1
    auth = delete_calls[0].request.headers.get("Authorization", "")
    assert auth == f"Bearer {ADMIN_TOKEN}"
