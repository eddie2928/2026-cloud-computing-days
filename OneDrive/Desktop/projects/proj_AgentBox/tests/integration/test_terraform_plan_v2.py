"""Terraform plan assertions for Task-4 changes.
Extends Task-3 assertions with: kb_staging absent + 2 action_groups + list_project_files present.
"""
import pytest
from tests.terraform.conftest import find_resource

pytestmark = pytest.mark.terraform


def test_kb_staging_not_in_plan(tf_plan_json):
    changes = tf_plan_json.get("resource_changes", [])
    kb_addrs = [c["address"] for c in changes if "kb_staging" in c["address"]]
    assert not kb_addrs, f"kb_staging resources must not exist in plan: {kb_addrs}"


def test_action_group_count_ge_2(tf_plan_json):
    changes = tf_plan_json.get("resource_changes", [])
    count = sum(
        1 for c in changes
        if c["address"].startswith("aws_bedrockagent_agent_action_group.")
    )
    assert count >= 2, f"Expected >= 2 action_group resources, got {count}"


def test_list_project_files_action_group_present(tf_plan_json):
    find_resource(tf_plan_json, "aws_bedrockagent_agent_action_group.list_project_files")


def test_lambda_mcp_url_still_http_8080(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_lambda_function.mcp_bridge")
    env_vars = res["change"]["after"].get("environment", [{}])[0].get("variables", {})
    mcp_url = env_vars.get("MCP_SERVER_URL", "")
    assert mcp_url.startswith("http://"), f"MCP_SERVER_URL must start with http://"
    assert ":8080" in mcp_url, f"MCP_SERVER_URL must contain :8080"


def test_kb_staging_bucket_not_in_lambda_env(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_lambda_function.mcp_bridge")
    env_vars = res["change"]["after"].get("environment", [{}])[0].get("variables", {})
    assert "KB_STAGING_BUCKET" not in env_vars, "Lambda must not have KB_STAGING_BUCKET env var"
