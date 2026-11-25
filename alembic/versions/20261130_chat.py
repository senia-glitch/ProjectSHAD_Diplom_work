"""Personal chat between a tutor and a student.

Revision ID: 20261130_chat
Revises: 20261129_lesson_boards
"""
from alembic import op
import sqlalchemy as sa

revision = "20261130_chat"
down_revision = "20261129_lesson_boards"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_user_id", sa.Integer(), nullable=False),
        sa.Column("student_user_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tutor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_pair_id", "chat_messages", ["tutor_user_id", "student_user_id", "id"])


def downgrade():
    op.drop_index("ix_chat_messages_pair_id", table_name="chat_messages")
    op.drop_table("chat_messages")
