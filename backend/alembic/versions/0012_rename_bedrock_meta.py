"""rename bedrock_meta to claude_meta

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-05
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("qna_items", "bedrock_meta", new_column_name="claude_meta")
    op.alter_column("diary_entries", "bedrock_meta", new_column_name="claude_meta")


def downgrade() -> None:
    op.alter_column("qna_items", "claude_meta", new_column_name="bedrock_meta")
    op.alter_column("diary_entries", "claude_meta", new_column_name="bedrock_meta")
