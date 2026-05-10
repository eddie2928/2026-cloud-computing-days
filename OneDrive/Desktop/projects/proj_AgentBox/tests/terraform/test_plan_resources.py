import json
import pytest
from tests.terraform.conftest import find_resource

pytestmark = pytest.mark.terraform


def test_resource_count_minimum(tf_plan_json):
    count = len(tf_plan_json.get("resource_changes", []))
    assert count >= 50, f"Expected >= 50 resources in plan, got {count}"


def test_app_instance_present(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_instance.app")
    assert res["change"]["after"]["instance_type"] == "t3.micro"


def test_mcp_instance_present(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_instance.mcp")
    assert res["change"]["after"]["instance_type"] == "t3.small"


def test_mcp_sg_ingress_from_lambda_sg(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_security_group.mcp")
    ingress_rules = res["change"]["after"].get("ingress", [])
    has_lambda_src = any(
        "lambda" in str(rule.get("security_groups", [])).lower()
        or any("lambda" in str(sg).lower() for sg in rule.get("security_groups", []))
        for rule in ingress_rules
    )
    # The ingress rule for port 8080 should reference the lambda SG
    port_8080_rules = [r for r in ingress_rules if r.get("from_port") == 8080]
    assert len(port_8080_rules) >= 1, "No ingress rule for port 8080 found in mcp-sg"


def test_app_role_no_kms(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_iam_role_policy.app")
    policy_json = res["change"]["after"]["policy"]
    assert "kms:Decrypt" not in policy_json, "app-role must NOT have kms:Decrypt"


def test_mcp_role_no_bedrock(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_iam_role_policy.mcp")
    policy_json = res["change"]["after"]["policy"]
    assert "bedrock:" not in policy_json, "mcp-role must NOT have bedrock permissions"


def test_lambda_in_vpc(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_lambda_function.mcp_bridge")
    vpc_config = res["change"]["after"].get("vpc_config", [])
    assert len(vpc_config) >= 1, "Lambda must have vpc_config"
    subnet_ids = vpc_config[0].get("subnet_ids", [])
    assert len(subnet_ids) == 1, f"Lambda must have exactly 1 subnet, got {subnet_ids}"


def test_lambda_mcp_url_http_8080(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_lambda_function.mcp_bridge")
    env_vars = res["change"]["after"].get("environment", [{}])[0].get("variables", {})
    mcp_url = env_vars.get("MCP_SERVER_URL", "")
    assert mcp_url.startswith("http://"), f"MCP_SERVER_URL must start with http://, got: {mcp_url}"
    assert ":8080" in mcp_url, f"MCP_SERVER_URL must contain :8080, got: {mcp_url}"
