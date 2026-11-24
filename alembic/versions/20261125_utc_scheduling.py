"""UTC time, booking confirmation, link consent, absence periods, lesson status history.

Revision ID: 20261125_utc_scheduling
Revises: 20261124_modules

До этой ревизии наивные даты хранились по «стенным» часам сервера (пояс контейнеров,
по умолчанию Asia/Irkutsk). Теперь сервер хранит и считает только UTC, а личный пояс
пользователя (timezone_offset, часы) — лишь способ показа.

Исходный пояс берётся из SHAD_LEGACY_TIMEZONE (compose передаёт прежний SHAD_TIMEZONE),
иначе — из настройки TIMEZONE сессии БД. Чтобы у существующих пользователей ничего
не сдвинулось на экране, их личный пояс выставляется в смещение прежнего серверного:
раньше они видели именно его, а еженедельные брони были заданы в этих же часах.
"""
import datetime
import os
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa

revision = "20261125_utc_scheduling"
down_revision = "20261124_modules"
branch_labels = None
depends_on = None

NAIVE_COLUMNS = {
    "users": ("created_at",),
    "bookings": ("created_at", "updated_at"),
    "lessons": ("created_at", "updated_at", "start_time", "end_time"),
    "lesson_participants": ("created_at", "updated_at"),
    "notifications": ("created_at", "read_at"),
}


def _legacy_zone(connection) -> str:
    zone = os.getenv("SHAD_LEGACY_TIMEZONE")
    if not zone:
        zone = connection.execute(sa.text("SELECT current_setting('TIMEZONE')")).scalar()
    return zone or "UTC"


def _offset_hours(zone: str) -> int:
    offset = datetime.datetime.now(ZoneInfo(zone)).utcoffset() or datetime.timedelta()
    return round(offset.total_seconds() / 3600)


def _shift(connection, source: str, target: str) -> None:
    """Наивное время из пояса source в пояс target (по правилам пояса на каждую дату)."""
    for table, columns in NAIVE_COLUMNS.items():
        sets = ", ".join(
            f'"{c}" = ("{c}" AT TIME ZONE :source) AT TIME ZONE :target' for c in columns
        )
        connection.execute(sa.text(f'UPDATE "{table}" SET {sets}'), {"source": source, "target": target})


def upgrade():
    connection = op.get_bind()
    zone = _legacy_zone(connection)
    if zone.upper() not in ("UTC", "ETC/UTC", "GMT"):
        _shift(connection, zone, "UTC")
    offset = _offset_hours(zone)
    connection.execute(sa.text('UPDATE "tutor_settings" SET timezone_offset = :o'), {"o": offset})
    connection.execute(sa.text('UPDATE "student_settings" SET timezone_offset = :o'), {"o": offset})

    true = sa.text("true")
    op.add_column("student_settings", sa.Column("require_link_consent", sa.Boolean(), nullable=False, server_default=true))
    op.add_column("tutor_settings", sa.Column("auto_confirm_bookings", sa.Boolean(), nullable=False, server_default=true))
    op.add_column("tutor_settings", sa.Column("require_link_consent", sa.Boolean(), nullable=False, server_default=true))
    op.add_column("tutor_settings", sa.Column("absence_status", sa.String(length=20), nullable=True))
    op.add_column("tutor_settings", sa.Column("absence_from", sa.DateTime(), nullable=True))
    op.add_column("tutor_settings", sa.Column("absence_to", sa.DateTime(), nullable=True))
    op.add_column("configurations", sa.Column("auto_confirm_bookings", sa.Boolean(), nullable=False, server_default=true))
    op.add_column("configurations", sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"))
    op.add_column("configurations", sa.Column("requested_by", sa.String(length=20), nullable=True))
    op.add_column("configurations", sa.Column("requested_at", sa.DateTime(), nullable=True))
    op.add_column("lessons", sa.Column("status_history", sa.JSON(), nullable=True))
    # Прежний статус «Отпуск/Болею» без дат переносится в открытый период с текущего момента
    # на 30 дней: дальше репетитор сам задаёт границы.
    connection.execute(sa.text(
        "UPDATE tutor_settings SET absence_status = work_status, "
        "absence_from = (now() AT TIME ZONE 'UTC'), "
        "absence_to = (now() AT TIME ZONE 'UTC') + interval '30 days', work_status = 'WORKING' "
        "WHERE work_status IN ('VACATION', 'SICK')"
    ))


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text(
        "UPDATE tutor_settings SET work_status = absence_status WHERE absence_status IS NOT NULL"
    ))
    op.drop_column("lessons", "status_history")
    for column in ("requested_at", "requested_by", "status", "auto_confirm_bookings"):
        op.drop_column("configurations", column)
    for column in ("absence_to", "absence_from", "absence_status", "require_link_consent", "auto_confirm_bookings"):
        op.drop_column("tutor_settings", column)
    op.drop_column("student_settings", "require_link_consent")
    zone = _legacy_zone(connection)
    if zone.upper() not in ("UTC", "ETC/UTC", "GMT"):
        _shift(connection, "UTC", zone)
