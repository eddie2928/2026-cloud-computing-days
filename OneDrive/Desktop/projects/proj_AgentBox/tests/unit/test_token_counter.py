"""Unit tests verifying _increment_token_count is called after Bedrock invoke."""
import os
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
from datetime import datetime, timezone


PROJECT = "agentbox"
REGION = "us-east-1"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", PROJECT)
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("BEDROCK_AGENT_ID", "test-agent")
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", "test-alias")
    monkeypatch.setenv("ADMIN_TOKEN", "token")
    monkeypatch.setenv("MCP_SERVER_URL", "http://mcp:8080")


@mock_aws
def test_token_counter_incremented_after_bedrock(monkeypatch):
    import importlib
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

    # Reload to pick up moto-patched boto3
    importlib.reload(srv)

    fake_chunks = ["This ", "is ", "a ", "test ", "response."]

    def fake_invoke(*args, **kwargs):
        return {
            "completion": [
                {"chunk": {"bytes": c.encode()}} for c in fake_chunks
            ]
        }

    with patch.object(srv._bedrock_runtime, "invoke_agent", side_effect=fake_invoke):
        verdict, reasons = srv._invoke_bedrock_agent("test prompt", "sess-1")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    table = dynamo.Table(f"{PROJECT}-settings")
    item = table.get_item(Key={"key": f"bedrock_tokens_{today}"})
    assert "Item" in item, "Token counter item should exist in DynamoDB"
    assert int(item["Item"]["value"]) > 0, "Token count should be positive"
