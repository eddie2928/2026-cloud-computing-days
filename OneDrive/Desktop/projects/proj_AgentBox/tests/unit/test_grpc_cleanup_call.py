"""Task-4: verify grpc Inspect no longer calls MCP cleanup (cleanup removed)."""
import importlib
from unittest.mock import MagicMock, patch

import pytest
import responses as resp_lib

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
def test_inspect_does_not_call_mcp_cleanup(monkeypatch):
    """Task-4: cleanup endpoint removed, Inspect must not call DELETE /mcp/cleanup."""
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    with patch.object(srv, "_invoke_bedrock_agent", return_value=("ALLOW", [])), \
         patch.object(srv, "_record_event"), \
         patch.object(srv, "_daily_token_count", return_value=0), \
         patch.object(srv, "_increment_token_count"):

        servicer = srv.InspectorServicer()
        request = MagicMock()
        request.prompt = "is this code safe?"
        request.user_id = "test-user"
        result = servicer.Inspect(request, MagicMock())

    assert result.verdict == "ALLOW"
    delete_calls = [c for c in resp_lib.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 0, "cleanup must not be called in Task-4"


@resp_lib.activate
def test_no_cleanup_on_block(monkeypatch):
    """Task-4: BLOCK verdict also must not trigger cleanup."""
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    with patch.object(srv, "_invoke_bedrock_agent", return_value=("BLOCK", ["bad"])), \
         patch.object(srv, "_record_event"), \
         patch.object(srv, "_daily_token_count", return_value=0), \
         patch.object(srv, "_increment_token_count"):

        servicer = srv.InspectorServicer()
        request = MagicMock()
        request.prompt = "bad prompt"
        request.user_id = "u"
        result = servicer.Inspect(request, MagicMock())

    delete_calls = [c for c in resp_lib.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 0
