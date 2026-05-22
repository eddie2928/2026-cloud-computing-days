"""profile and emotion

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nickname", sa.Text(), nullable=False),
        sa.Column("gender", sa.Text(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("occupation", sa.Text(), nullable=True),
        sa.Column("hobbies", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("interests", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("notification_time", sa.Time(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint("age > 0 AND age < 150", name="ck_profile_age"),
    )

    op.add_column(
        "diary_entries",
        sa.Column("emotion", sa.Text(), nullable=False, server_default="neutral"),
    )
    op.create_check_constraint(
        "ck_diary_emotion",
        "diary_entries",
        "emotion IN ('happy','sad','angry','neutral','bored')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_diary_emotion", "diary_entries", type_="check")
    op.drop_column("diary_entries", "emotion")
    op.drop_table("user_profiles")
