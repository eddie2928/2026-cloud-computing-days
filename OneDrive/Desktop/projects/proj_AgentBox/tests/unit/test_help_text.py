"""Unit tests for agentbox --help output (Task-7 N3~N7)."""
import subprocess
import sys

import pytest


def _run_help(*args) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "agentbox"] + list(args) + ["--help"],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout + result.stderr


# ── T1: --help에 7개 흐름 키워드 전부 포함 ───────────────────────────────────
def test_main_help_keywords():
    out = _run_help()
    for keyword in [
        "deploy.sh",
        "agentbox set",
        "agentbox init",
        "agentbox on",
        "agentbox off",
        "agentbox doctor",
        "agentbox status",
        "agentbox reset",
        "agentbox destroy",
        "destroy.sh",
    ]:
        assert keyword in out, f"Missing keyword in --help: {keyword!r}"


# ── T2: 제거된 키워드 부재: agentbox ca, agentbox setup ──────────────────────
def test_removed_subcommands_absent():
    out = _run_help()
    # These should NOT appear as top-level subcommand descriptions in --help
    # (they were removed from the subcommand list)
    lines = [l.strip() for l in out.splitlines()]
    # Check that "ca" and "setup" don't appear as subcommand names in help listing
    assert "agentbox ca" not in out, "'agentbox ca' should not be in --help"
    assert "agentbox setup" not in out, "'agentbox setup' should not be in --help"


# ── T3: doctor --help에 "D1", "--json", "--fix", "read-only" 포함 ─────────────
def test_doctor_help():
    out = _run_help("doctor")
    for kw in ["D1", "--json", "--fix", "read-only"]:
        assert kw in out, f"Missing in doctor --help: {kw!r}"


# ── T4: set --help에 "7a", "7b", "7c", "mTLS handshake" 포함 ────────────────
def test_set_help_mentions_steps():
    out = _run_help("set")
    for kw in ["7a", "7b", "7c", "mTLS"]:
        assert kw in out, f"Missing in set --help: {kw!r}"


# ── T5: _on/_off は argparse.SUPPRESS で登録されている ───────────────────────
def test_hidden_subcommands_use_suppress():
    """_on/_off should be registered with argparse.SUPPRESS (not exposed as public commands)."""
    from agentbox.__main__ import main
    import argparse, io

    # Check that _on/_off are NOT in the visible subcommand help listing
    out = _run_help()
    lines = out.splitlines()
    # If they appear, they should only appear with SUPPRESS marker (hidden)
    # Verify they're not listed alongside regular commands like "set", "init", "run"
    for line in lines:
        stripped = line.strip()
        # A visible help entry looks like "  cmd   description"
        # SUPPRESS should make them not show up as "  _on   [something useful]"
        if stripped.startswith("_on") and "SUPPRESS" not in stripped:
            pytest.fail(f"_on appears as visible subcommand: {line!r}")
        if stripped.startswith("_off") and "SUPPRESS" not in stripped:
            pytest.fail(f"_off appears as visible subcommand: {line!r}")
