from datetime import datetime
from typing import Literal

from pydantic import BaseModel, HttpUrl


class PromptEvent(BaseModel):
    id: str
    created_at: datetime
    resolved_at: datetime | None = None
    source: str = "claude_code"
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    url: str
    request_headers: dict[str, str]
    request_body: str | None = None
    prompt_excerpt: str = ""
    status: Literal["pending", "allowed", "blocked", "failed"] = "pending"
    verdict_by: str | None = None
    upstream_status_code: int | None = None
    error: str | None = None


class Verdict(BaseModel):
    decision: Literal["allow", "block"]
    reason: str | None = None


class WSMessage(BaseModel):
    type: Literal["event_created", "verdict_set", "event_completed"]
    event: PromptEvent
