"""Admin panel: key login, user blocking, admin audit log.

Revision ID: 20261126_admin_panel
Revises: 20261125_utc_scheduling
"""
from alembic import op
import sqlalchemy as sa

revision = "20261126_admin_panel"
down_revision = "20261125_utc_scheduling"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("block_reason", sa.String(length=500), nullable=True))
    op.add_column("admins", sa.Column("key_hash", sa.String(length=64), nullable=True))
    op.add_column("admins", sa.Column("key_created_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("admins_key_hash_key", "admins", ["key_hash"])
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_created_at", "admin_audit", ["created_at"])


def downgrade():
    op.drop_index("ix_admin_audit_created_at", table_name="admin_audit")
    op.drop_table("admin_audit")
    op.drop_constraint("admins_key_hash_key", "admins", type_="unique")
    op.drop_column("admins", "key_created_at")
    op.drop_column("admins", "key_hash")
    op.drop_column("users", "block_reason")
    op.drop_column("users", "blocked_at")
