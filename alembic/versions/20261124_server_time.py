"""Preserve the project's server wall time with SQLModel 0.0.48.

Revision ID: 20261124_server_time
Revises: 35a2d259c8b6
"""
from alembic import op
import sqlalchemy as sa

revision = "20261124_server_time"
down_revision = "35a2d259c8b6"
branch_labels = None
depends_on = None

TIME_COLUMNS = {
    "users": ("created_at",),
    "bookings": ("created_at", "updated_at"),
    "lessons": ("created_at", "updated_at", "start_time", "end_time"),
    "lesson_participants": ("created_at", "updated_at"),
    "notifications": ("created_at", "read_at"),
}


def _convert(timezone: bool):
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for table, columns in TIME_COLUMNS.items():
        actual = {c["name"]: c["type"] for c in inspector.get_columns(table)}
        for column in columns:
            old_type = actual[column]
            if bool(old_type.timezone) != timezone:
                op.alter_column(
                    table, column, existing_type=old_type,
                    type_=sa.DateTime(timezone=timezone),
                    postgresql_using=f'"{column}" AT TIME ZONE current_setting(\'TIMEZONE\')',
                )


def upgrade():
    _convert(False)


def downgrade():
    _convert(True)
