from datetime import date, datetime, time
from typing import Annotated, Literal, Optional

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
    start_time: str | None = None
    end_time: str | None = None


class QnAStartResponse(BaseModel):
    session_id: int
    question: str
    sequence: int
    history: list[QnAHistoryItem] = Field(default_factory=list)
    pending_schedules: list[PendingSchedule] = []
    suggestions: list[str] = []


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
    suggestions: list[str] = []
    min_reached: bool = False


class ScheduleOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    start_time: time | None = None
    end_time: time | None = None
    situation: str

    model_config = {"from_attributes": True}


class ScheduleUpdate(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    situation: str | None = None


class ScheduleConfirm(BaseModel):
    period_start: date
    period_end: date
    start_time: time | None = None
    end_time: time | None = None
    situation: str


class CalendarEntry(BaseModel):
    date: date
    emotion: str
    written_date: date | None = None


class HolidayOut(BaseModel):
    date: date
    name: str
    is_holiday: bool

    model_config = {"from_attributes": True}


class CalendarResponse(BaseModel):
    entries: list[CalendarEntry]
    schedules: list[ScheduleOut] = []
    holidays: list[HolidayOut] = []


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


class QnAUndoRequest(BaseModel):
    session_id: int
    target_sequence: int
    mode: Literal["keep", "discard"]
    new_answer: str | None = None


class QnAUndoResponse(BaseModel):
    question: str
    sequence: int
    suggestions: list[str] = []
    pending_schedules: list[PendingSchedule] = []
    removed_schedule_keys: list[str] = []


class QnAFinalizeRequest(BaseModel):
    session_id: int


class QnAFinalizeResponse(BaseModel):
    diary: str


class PlanTodoOut(BaseModel):
    id: int
    plan_id: int
    todo_date: date
    sequence: int
    content: str
    completed: bool
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PlanTodoCreate(BaseModel):
    todo_date: date
    sequence: int
    content: str


class PlanTodoUpdate(BaseModel):
    sequence: int | None = None
    content: str | None = None
    completed: bool | None = None


class PlanOut(BaseModel):
    id: int
    user_id: int
    title: str
    description_input: str | None = None
    goal_input: str | None = None
    period_start: date
    period_end: date
    source: str
    created_at: datetime
    progress: float = 0.0

    model_config = {"from_attributes": True}


class PlanWithTodosOut(PlanOut):
    todos: list[PlanTodoOut] = []


class PlanCreate(BaseModel):
    title: str
    period_start: date
    period_end: date
    description_input: str | None = None
    goal_input: str | None = None
    source: str = "manual"


class PlanUpdate(BaseModel):
    title: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    description_input: str | None = None
    goal_input: str | None = None


class PlanGenerateInput(BaseModel):
    description: str
    period_start: date
    period_end: date
    goal: str


class PlanTodoBulkReplace(BaseModel):
    contents: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list,
        max_length=50,
    )


class TasteProfileIn(BaseModel):
    music_genres: list[str] = []
    favorite_artists: list[str] = []
    preferred_music_mood: list[str] = []
    mbti: Optional[str] = None
    ideal_type: Optional[str] = None
    personality_keywords: list[str] = []
    movie_genres: list[str] = []
    food_preferences: list[str] = []
    life_values: list[str] = []
    weekend_style: Optional[str] = None
    love_language: Optional[str] = None
    answers: Optional[dict] = None
    completed: bool = False

    def model_post_init(self, __context):
        if self.mbti == "":
            self.mbti = None


class TasteProfileOut(BaseModel):
    music_genres: list[str]
    favorite_artists: list[str]
    preferred_music_mood: list[str]
    mbti: Optional[str]
    ideal_type: Optional[str]
    personality_keywords: list[str]
    movie_genres: list[str]
    food_preferences: list[str]
    life_values: list[str]
    weekend_style: Optional[str]
    love_language: Optional[str]
    answers: Optional[dict]
    completed: bool

    model_config = {"from_attributes": True}
