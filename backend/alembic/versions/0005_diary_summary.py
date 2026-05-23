"""diary summary column

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-23
"""

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "diary_entries",
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("diary_entries", "summary")
