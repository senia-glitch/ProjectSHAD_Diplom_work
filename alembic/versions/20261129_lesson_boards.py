"""Lesson boards: one board per lesson, no access code.

Revision ID: 20261129_lesson_boards
Revises: 20261128_site_blocks
"""
from alembic import op
import sqlalchemy as sa

revision = "20261129_lesson_boards"
down_revision = "20261128_site_blocks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("boards", sa.Column("lesson_id", sa.Integer(), nullable=True))
    op.create_unique_constraint("boards_lesson_id_key", "boards", ["lesson_id"])
    op.create_foreign_key("boards_lesson_id_fkey", "boards", "lessons", ["lesson_id"], ["id"], ondelete="CASCADE")


def downgrade():
    op.drop_constraint("boards_lesson_id_fkey", "boards", type_="foreignkey")
    op.drop_constraint("boards_lesson_id_key", "boards", type_="unique")
    op.drop_column("boards", "lesson_id")
