import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from agentbox.models import PromptEvent, Verdict, WSMessage


def _base_event(**kwargs):
    defaults = dict(
        id="abc123",
        created_at=datetime.now(timezone.utc),
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        request_headers={"content-type": "application/json"},
        status="pending",
    )
    defaults.update(kwargs)
    return defaults


def test_prompt_event_valid():
    ev = PromptEvent(**_base_event())
    assert ev.status == "pending"
    assert ev.method == "POST"


def test_prompt_event_invalid_status():
    with pytest.raises(ValidationError):
        PromptEvent(**_base_event(status="unknown"))


def test_prompt_event_invalid_method():
    with pytest.raises(ValidationError):
        PromptEvent(**_base_event(method="BREW"))


def test_verdict_allow():
    v = Verdict(decision="allow")
    assert v.decision == "allow"
    assert v.reason is None


def test_verdict_block_with_reason():
    v = Verdict(decision="block", reason="policy violation")
    assert v.reason == "policy violation"


def test_verdict_invalid_decision():
    with pytest.raises(ValidationError):
        Verdict(decision="maybe")


def test_ws_message_roundtrip():
    ev = PromptEvent(**_base_event())
    msg = WSMessage(type="event_created", event=ev)
    raw = msg.model_dump_json()
    restored = WSMessage.model_validate_json(raw)
    assert restored.event.id == ev.id


def test_ws_message_invalid_type():
    ev = PromptEvent(**_base_event())
    with pytest.raises(ValidationError):
        WSMessage(type="unknown_type", event=ev)
