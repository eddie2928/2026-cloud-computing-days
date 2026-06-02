"""user_schedules에 start_time/end_time 컬럼 추가

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_schedules", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("user_schedules", sa.Column("end_time", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_schedules", "end_time")
    op.drop_column("user_schedules", "start_time")
