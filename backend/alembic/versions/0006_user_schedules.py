"""user schedules table

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-23
"""

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "user_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("situation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_schedules_user_period",
        "user_schedules",
        ["user_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_schedules_user_period", table_name="user_schedules")
    op.drop_table("user_schedules")
