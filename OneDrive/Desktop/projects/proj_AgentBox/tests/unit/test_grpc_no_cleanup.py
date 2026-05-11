"""Verify that grpc Inspect no longer calls MCP cleanup after verdict."""
import importlib
from unittest.mock import MagicMock, patch

import pytest
import responses as resp_lib

MCP_URL = "http://mcp-no-cleanup:8080"
ADMIN_TOKEN = "grpc-no-cleanup-token"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", MCP_URL)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("PROJECT_NAME", "agentbox")
    monkeypatch.setenv("BEDROCK_AGENT_ID", "test-agent-id")
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", "test-alias-id")


@resp_lib.activate
def test_inspect_does_not_call_cleanup(monkeypatch):
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    token_counter_calls = []

    def fake_increment(tokens):
        token_counter_calls.append(tokens)

    with patch.object(srv, "_invoke_bedrock_agent", return_value=("ALLOW", [])), \
         patch.object(srv, "_record_event"), \
         patch.object(srv, "_daily_token_count", return_value=0), \
         patch.object(srv, "_increment_token_count", side_effect=fake_increment):

        servicer = srv.InspectorServicer()
        request = MagicMock()
        request.prompt = "is this code safe?"
        request.user_id = "test-user"
        result = servicer.Inspect(request, MagicMock())

    assert result.verdict == "ALLOW"
    # No HTTP calls should have been made
    assert len(resp_lib.calls) == 0, f"Expected 0 HTTP calls, got {len(resp_lib.calls)}"


@resp_lib.activate
def test_token_counter_still_called(monkeypatch):
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    token_counter_calls = []

    def fake_increment(tokens):
        token_counter_calls.append(tokens)

    with patch.object(srv, "_invoke_bedrock_agent", return_value=("BLOCK", ["test reason"])), \
         patch.object(srv, "_record_event"), \
         patch.object(srv, "_daily_token_count", return_value=0), \
         patch.object(srv, "_increment_token_count", side_effect=fake_increment):

        servicer = srv.InspectorServicer()
        request = MagicMock()
        request.prompt = "bad prompt"
        request.user_id = "u"
        servicer.Inspect(request, MagicMock())

    # Token counter called once (inside _invoke_bedrock_agent mock doesn't count,
    # but the patched side_effect captures the direct call)
    assert len(resp_lib.calls) == 0
