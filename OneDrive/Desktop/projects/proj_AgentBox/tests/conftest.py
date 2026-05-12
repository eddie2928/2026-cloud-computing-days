import asyncio
import os
import tempfile
import pytest

from agentbox.api.hitl import HITLQueue
from agentbox.api.ws import WSHub


@pytest.fixture(autouse=True)
def agentbox_home(tmp_path, monkeypatch):
    """Redirect AGENTBOX_HOME to a temp dir so tests never write to real ~/.agentbox/."""
    if not os.environ.get("AGENTBOX_HOME"):
        monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def hitl_queue():
    return HITLQueue()


@pytest.fixture
def ws_hub():
    return WSHub()


@pytest.fixture(autouse=True)
def aws_credentials_env(monkeypatch):
    """Set fake AWS credentials so moto doesn't try real AWS."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "test")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test")


@pytest.fixture
def mock_aws_stack():
    """Start moto and create KMS key + S3 buckets + DynamoDB tables."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        region = "us-east-1"
        project = "agentbox"

        kms = boto3.client("kms", region_name=region)
        key = kms.create_key(Description="test-key")
        kms_key_id = key["KeyMetadata"]["KeyId"]
        kms_key_arn = key["KeyMetadata"]["Arn"]

        s3 = boto3.client("s3", region_name=region)
        s3.create_bucket(Bucket=f"{project}-encrypted-code")
        s3.create_bucket(Bucket=f"{project}-kb-staging")

        dynamo = boto3.resource("dynamodb", region_name=region)
        dynamo.create_table(
            TableName=f"{project}-events",
            KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamo.create_table(
            TableName=f"{project}-settings",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield {
            "kms_key_id": kms_key_id,
            "kms_key_arn": kms_key_arn,
            "project": project,
            "region": region,
        }


@pytest.fixture
def admin_token():
    return "test-admin-token"
