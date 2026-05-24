from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str


class StreakResponse(BaseModel):
    streak: int


class QnAStartRequest(BaseModel):
    diary_date: date


class QnAHistoryItem(BaseModel):
    sequence: int
    question: str
    answer: str


class PendingSchedule(BaseModel):
    period_start: str
    period_end: str
    situation: str


class QnAStartResponse(BaseModel):
    session_id: int
    question: str
    sequence: int
    history: list[QnAHistoryItem] = Field(default_factory=list)
    pending_schedules: list[PendingSchedule] = []


class QnAAnswerRequest(BaseModel):
    session_id: int
    sequence: int
    answer: str


class QnAAnswerResponse(BaseModel):
    next_question: str | None = None
    sequence: int | None = None
    completed: bool
    diary: str | None = None
    pending_schedules: list[PendingSchedule] = []


class ScheduleOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    situation: str

    model_config = {"from_attributes": True}


class ScheduleUpdate(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    situation: str | None = None


class ScheduleConfirm(BaseModel):
    period_start: date
    period_end: date
    situation: str


class CalendarEntry(BaseModel):
    date: date
    emotion: str


class CalendarResponse(BaseModel):
    entries: list[CalendarEntry]
    schedules: list[ScheduleOut] = []


class DiaryResponse(BaseModel):
    date: date
    body: str
    summary: str
    emotion: str


class UserProfileIn(BaseModel):
    nickname: str
    gender: str = Field(..., pattern="^(male|female|other|private)$")
    age: int = Field(..., gt=0, lt=150)
    occupation: Optional[str] = None
    hobbies: list[str] = []
    interests: list[str] = []
    notification_time: Optional[time] = None  # TODO: Phase 3 추후 구현 예정


class UserProfileOut(BaseModel):
    nickname: str
    gender: str
    age: int
    occupation: Optional[str]
    hobbies: list[str]
    interests: list[str]
    notification_time: Optional[time]

    model_config = {"from_attributes": True}


class EmotionUpdate(BaseModel):
    emotion: str = Field(..., pattern="^(happy|sad|angry|neutral|bored)$")


class DiaryBodyUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class ShareCreateResponse(BaseModel):
    token: str
    url: str
    expires_at: str


class SharedDiaryResponse(BaseModel):
    date: date
    body: str
    emotion: str


class PetResponse(BaseModel):
    level: int
    xp: int
    xp_to_next: int


class DiarySearchItem(BaseModel):
    date: date
    snippet: str
    emotion: str


class DiarySearchResponse(BaseModel):
    results: list[DiarySearchItem]


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushPublicKeyOut(BaseModel):
    public_key: str
