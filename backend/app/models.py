from datetime import date, datetime, time

from sqlalchemy import (
    DATE,
    SMALLINT,
    TEXT,
    TIME,
    CheckConstraint,
    DateTime,
    ForeignKey,
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
    sessions: Mapped[list["QnASession"]] = relationship(back_populates="user")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(back_populates="user")


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
    bedrock_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
    emotion: Mapped[str] = mapped_column(TEXT, nullable=False, server_default="neutral")
    bedrock_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["QnASession"] = relationship(back_populates="diary_entry")
    user: Mapped["User"] = relationship(back_populates="diary_entries")
