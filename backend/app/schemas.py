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


class QnAStartResponse(BaseModel):
    session_id: int
    question: str
    sequence: int
    history: list[QnAHistoryItem] = Field(default_factory=list)


class QnAAnswerRequest(BaseModel):
    session_id: int
    sequence: int
    answer: str


class QnAAnswerResponse(BaseModel):
    next_question: str | None = None
    sequence: int | None = None
    completed: bool
    diary: str | None = None


class CalendarEntry(BaseModel):
    date: date
    emotion: str


class CalendarResponse(BaseModel):
    entries: list[CalendarEntry]


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
    notification_time: Optional[time] = None


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
