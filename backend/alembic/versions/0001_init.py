"""init

Revision ID: 0001
Revises:
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.TEXT(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    op.execute("INSERT INTO users (id, display_name) VALUES (1, 'default-user')")

    op.create_table(
        "qna_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("diary_date", sa.DATE(), nullable=False),
        sa.Column("status", sa.TEXT(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "diary_date", name="uq_session_user_date"),
    )

    op.create_table(
        "qna_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("qna_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.SMALLINT(), nullable=False),
        sa.Column("question", sa.TEXT(), nullable=False),
        sa.Column("answer", sa.TEXT(), nullable=True),
        sa.Column("rag_context", JSONB(), nullable=True),
        sa.Column("bedrock_meta", JSONB(), nullable=True),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_id", "sequence", name="uq_item_session_seq"),
    )

    op.create_table(
        "diary_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("qna_sessions.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("diary_date", sa.DATE(), nullable=False),
        sa.Column("body", sa.TEXT(), nullable=False),
        sa.Column("bedrock_meta", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.UniqueConstraint("user_id", "diary_date", name="uq_diary_user_date"),
    )


def downgrade() -> None:
    op.drop_table("diary_entries")
    op.drop_table("qna_items")
    op.drop_table("qna_sessions")
    op.drop_table("users")
