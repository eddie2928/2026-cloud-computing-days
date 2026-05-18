from datetime import date

from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


class QnAStartRequest(BaseModel):
    diary_date: date


class QnAStartResponse(BaseModel):
    session_id: int
    question: str
    sequence: int


class QnAAnswerRequest(BaseModel):
    session_id: int
    sequence: int
    answer: str


class QnAAnswerResponse(BaseModel):
    next_question: str | None = None
    sequence: int | None = None
    completed: bool
    diary: str | None = None


class CalendarResponse(BaseModel):
    dates: list[date]


class DiaryResponse(BaseModel):
    date: date
    body: str
