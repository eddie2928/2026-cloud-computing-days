"""Integration test: gRPC full flow v2 - cleanup removed, token counter still works."""
import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
import responses as resp_lib
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
MCP_URL = "http://mcp-v2:8080"
ADMIN_TOKEN = "grpc-v2-token"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", PROJECT)
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("MCP_SERVER_URL", MCP_URL)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BEDROCK_AGENT_ID", "test-agent")
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", "test-alias")


@mock_aws
@resp_lib.activate
def test_grpc_full_flow_no_cleanup(monkeypatch):
    """ALLOW verdict -> no cleanup call -> token counter incremented -> event recorded."""
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    dynamo = boto3.resource("dynamodb", region_name=REGION)
    dynamo.create_table(
        TableName=f"{PROJECT}-settings",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamo.create_table(
        TableName=f"{PROJECT}-events",
        KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    importlib.reload(srv)

    fake_chunks = ['{"verdict": "ALLOW", "reasons": []}']

    def fake_bedrock(*args, **kwargs):
        return {
            "completion": [{"chunk": {"bytes": c.encode()}} for c in fake_chunks]
        }

    with patch.object(srv._bedrock_runtime, "invoke_agent", side_effect=fake_bedrock):
        servicer = srv.InspectorServicer()
        request = MagicMock()
        request.prompt = "def safe_fn(): return True"
        request.user_id = "v2-test-user"
        result = servicer.Inspect(request, MagicMock())

    assert result.verdict == "ALLOW"

    # No HTTP calls (cleanup was removed)
    delete_calls = [c for c in resp_lib.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 0, f"Expected 0 DELETE calls, got {len(delete_calls)}"

    # Token counter was incremented
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    table = dynamo.Table(f"{PROJECT}-settings")
    item = table.get_item(Key={"key": f"bedrock_tokens_{today}"})
    assert "Item" in item
    assert int(item["Item"]["value"]) > 0

    # Event was recorded
    events_table = dynamo.Table(f"{PROJECT}-events")
    scan = events_table.scan()
    assert len(scan["Items"]) == 1
    assert scan["Items"][0]["verdict"] == "ALLOW"
