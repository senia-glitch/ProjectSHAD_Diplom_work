"""Profile photo URL, blog comment replies, blog post likes.

Revision ID: 20261127_social
Revises: 20261126_admin_panel
"""
from alembic import op
import sqlalchemy as sa

revision = "20261127_social"
down_revision = "20261126_admin_panel"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("blog_comments", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key("blog_comments_parent_id_fkey", "blog_comments", "blog_comments",
                          ["parent_id"], ["id"], ondelete="CASCADE")
    op.create_table(
        "blog_post_likes",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "user_id"),
    )


def downgrade():
    op.drop_table("blog_post_likes")
    op.drop_constraint("blog_comments_parent_id_fkey", "blog_comments", type_="foreignkey")
    op.drop_column("blog_comments", "parent_id")
    op.drop_column("users", "avatar_url")
