import json
import subprocess
import pytest


def find_resource(plan, address):
    """Return the resource_change entry matching address, fail if not found."""
    matches = [r for r in plan.get("resource_changes", []) if r["address"] == address]
    assert len(matches) == 1, f"Expected 1 resource with address '{address}', found {len(matches)}"
    return matches[0]


@pytest.fixture(scope="session")
def tf_plan_json(tmp_path_factory):
    out = tmp_path_factory.mktemp("tf") / "tf.plan"
    subprocess.run(
        ["terraform", "-chdir=infra", "init", "-upgrade=false", "-backend=false"],
        check=True,
    )
    subprocess.run(
        [
            "terraform", "-chdir=infra", "plan",
            "-refresh=false",
            "-var-file=../tests/terraform/test.tfvars",
            f"-out={out}",
        ],
        check=True,
    )
    raw = subprocess.check_output(
        ["terraform", "-chdir=infra", "show", "-json", str(out)]
    )
    return json.loads(raw)
