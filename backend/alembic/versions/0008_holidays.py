"""holidays table

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_holiday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )


def downgrade() -> None:
    op.drop_table("holidays")
