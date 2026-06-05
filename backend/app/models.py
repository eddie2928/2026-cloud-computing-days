from datetime import date, datetime, time

from sqlalchemy import (
    DATE,
    SMALLINT,
    TEXT,
    TIME,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
    taste_profile: Mapped["TasteProfile | None"] = relationship(back_populates="user", uselist=False)
    sessions: Mapped[list["QnASession"]] = relationship(back_populates="user")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(back_populates="user")
    plans: Mapped[list["Plan"]] = relationship(back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(TEXT, nullable=False)
    gender: Mapped[str] = mapped_column(TEXT, nullable=False)  # male|female|other|private
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    occupation: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    hobbies: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    interests: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    notification_time: Mapped[time | None] = mapped_column(TIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="profile")


class QnASession(Base):
    __tablename__ = "qna_sessions"
    __table_args__ = (UniqueConstraint("user_id", "diary_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    diary_date: Mapped[date] = mapped_column(DATE, nullable=False)
    status: Mapped[str] = mapped_column(TEXT, nullable=False)  # in_progress | completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    items: Mapped[list["QnAItem"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    diary_entry: Mapped["DiaryEntry | None"] = relationship(back_populates="session")


class QnAItem(Base):
    __tablename__ = "qna_items"
    __table_args__ = (UniqueConstraint("session_id", "sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qna_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    question: Mapped[str] = mapped_column(TEXT, nullable=False)
    answer: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    rag_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    claude_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["QnASession"] = relationship(back_populates="items")


EMOTION_VALUES = ('happy', 'sad', 'angry', 'neutral', 'bored')


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "diary_date"),
        CheckConstraint("emotion IN ('happy','sad','angry','neutral','bored')", name="ck_diary_emotion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qna_sessions.id"), unique=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    diary_date: Mapped[date] = mapped_column(DATE, nullable=False)
    body: Mapped[str] = mapped_column(TEXT, nullable=False)
    summary: Mapped[str] = mapped_column(TEXT, nullable=False, server_default="")
    emotion: Mapped[str] = mapped_column(TEXT, nullable=False, server_default="neutral")
    claude_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["QnASession"] = relationship(back_populates="diary_entry")
    user: Mapped["User"] = relationship(back_populates="diary_entries")


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    diary_date: Mapped[date] = mapped_column(DATE, nullable=False)
    token: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()


class Pet(Base):
    __tablename__ = "pet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_grew_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()


class UserSchedule(Base):
    __tablename__ = "user_schedules"
    __table_args__ = (
        Index("ix_user_schedules_user_period", "user_id", "period_start", "period_end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(DATE, nullable=False)
    period_end: Mapped[date] = mapped_column(DATE, nullable=False)
    start_time: Mapped[time | None] = mapped_column(TIME, nullable=True)
    end_time: Mapped[time | None] = mapped_column(TIME, nullable=True)
    situation: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(DATE, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    is_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(TEXT, nullable=False)
    auth: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="ck_plan_period"),
        Index("ix_plans_user_period", "user_id", "period_start", "period_end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    description_input: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    goal_input: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    period_start: Mapped[date] = mapped_column(DATE, nullable=False)
    period_end: Mapped[date] = mapped_column(DATE, nullable=False)
    source: Mapped[str] = mapped_column(TEXT, nullable=False, server_default="manual")
    ai_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="plans")
    todos: Mapped[list["PlanTodo"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    music_genres: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    favorite_artists: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    preferred_music_mood: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")

    mbti: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    ideal_type: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    personality_keywords: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    movie_genres: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    food_preferences: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")
    life_values: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False, server_default="{}")

    weekend_style: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    love_language: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="taste_profile")


class PlanTodo(Base):
    __tablename__ = "plan_todos"
    __table_args__ = (
        UniqueConstraint("plan_id", "todo_date", "sequence"),
        Index("ix_plan_todos_plan_date", "plan_id", "todo_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    todo_date: Mapped[date] = mapped_column(DATE, nullable=False)
    sequence: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped["Plan"] = relationship(back_populates="todos")
