"""1C-7: Unit tests for regex rules engine."""
from pathlib import Path

import pytest

from ec2.grpc_server.rules_engine import check_rules, load_rules

_RULES_PATH = str(Path(__file__).parent.parent.parent / "ec2" / "rules" / "rules.yaml")


@pytest.fixture
def rules():
    return load_rules(_RULES_PATH)


def test_aws_access_key_blocked(rules):
    prompt = "Please use AKIAIOSFODNN7EXAMPLE to authenticate"
    matches = check_rules(prompt, rules)
    assert any(m.rule_id == "aws_access_key" for m in matches)


def test_private_key_blocked(rules):
    prompt = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAK"
    matches = check_rules(prompt, rules)
    assert any(m.rule_id == "private_key_pem" for m in matches)


def test_api_key_blocked(rules):
    # Value must be alphanumeric only (no hyphens) to match [A-Za-z0-9/+]{16,}
    prompt = "API_KEY=abc123def456ghi789jkl012mno345pqrABC"
    matches = check_rules(prompt, rules)
    assert any(m.rule_id == "secret_key" for m in matches)


def test_db_conn_blocked(rules):
    prompt = "Connect using: postgresql://admin:secret@db.internal:5432/prod"
    matches = check_rules(prompt, rules)
    assert any(m.rule_id == "db_connection_string" for m in matches)


def test_clean_prompt_no_block(rules):
    prompt = "Explain Python list comprehensions with examples."
    matches = check_rules(prompt, rules)
    assert len(matches) == 0


def test_multiple_matches(rules):
    prompt = "AKIA1234567890ABCDEF password=supersecret123"
    matches = check_rules(prompt, rules)
    assert len(matches) >= 2
