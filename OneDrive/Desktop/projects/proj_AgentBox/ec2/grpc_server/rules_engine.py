"""1C-3: Regex ruleset engine for 1st-pass fast BLOCK."""
import re
from pathlib import Path
from typing import NamedTuple

import yaml


class RuleMatch(NamedTuple):
    rule_id: str
    reason: str


def load_rules(path: str | None = None) -> list[dict]:
    if path:
        rules_path = Path(path)
    else:
        # EC2 production path, fallback to repo-relative path
        prod_path = Path("/opt/agentbox/ec2/rules/rules.yaml")
        rules_path = prod_path if prod_path.exists() else Path(__file__).parent.parent / "rules" / "rules.yaml"
    with open(rules_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])


def check_rules(prompt: str, rules: list[dict]) -> list[RuleMatch]:
    matches = []
    for rule in rules:
        if re.search(rule["pattern"], prompt):
            matches.append(RuleMatch(rule_id=rule["id"], reason=rule["reason"]))
    return matches
