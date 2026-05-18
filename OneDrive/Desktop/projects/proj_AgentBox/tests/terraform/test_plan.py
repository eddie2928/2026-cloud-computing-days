"""Terraform plan verification: aws_eip + ingress 8443 (F1 + D3)."""
import pytest
from tests.terraform.conftest import find_resource

pytestmark = pytest.mark.tf_plan


def test_aws_eip_app_present(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_eip.app")
    assert res["change"]["actions"] == ["create"]


def test_aws_eip_mcp_present(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_eip.mcp")
    assert res["change"]["actions"] == ["create"]


def test_aws_eip_association_app(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_eip_association.app")
    assert res["change"]["actions"] == ["create"]


def test_aws_eip_association_mcp(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_eip_association.mcp")
    assert res["change"]["actions"] == ["create"]


def test_app_sg_ingress_8443(tf_plan_json):
    res = find_resource(tf_plan_json, "aws_security_group.app")
    ingress_rules = res["change"]["after"].get("ingress", [])
    rules_8443 = [r for r in ingress_rules if r.get("from_port") == 8443]
    assert len(rules_8443) >= 1, "app-sg must have ingress rule for port 8443 (upload proxy)"


def test_app_output_uses_eip(tf_plan_json):
    outputs = tf_plan_json.get("output_changes", {})
    assert "app_public_ip" in outputs, "app_public_ip output must exist"
