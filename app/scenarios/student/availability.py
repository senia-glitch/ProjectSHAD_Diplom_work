"""Свободные окна репетитора для ученика — единый расчёт для списка окон и записи.

Всё время — наивный UTC. Еженедельные брони заданы в «стенных» часах репетитора
(его личное смещение timezone_offset), поэтому окна строятся по местным датам
репетитора и переводятся в UTC. Из окон вычитаются: период отсутствия репетитора
(отпуск/болезнь), его занятые уроки и собственные уроки ученика.
"""
import datetime

from app.utils.clock import from_local, to_local, to_utc_naive
from app.utils.lessons import NON_BLOCKING_LESSON_STATUSES
from app.utils.participants import is_cancelled_row
from app.utils.schedule import get_available_slots, subtract_blocks

WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")


def _dt(value) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return to_utc_naive(value)
    return datetime.datetime.fromisoformat(str(value).replace(" ", "T"))


def booking_windows_utc(bookings: list, student_id: int, offset_hours, start, end) -> list[dict]:
    """Окна броней, доступные ученику, в UTC, обрезанные диапазоном [start, end)."""
    by_day: dict[str, list] = {}
    for b in bookings:
        by_day.setdefault(b.get("weekday"), []).append(b)
    local_day = to_local(start, offset_hours).date()
    last_day = to_local(end, offset_hours).date()
    windows = []
    while local_day <= last_day:
        midnight = datetime.datetime.combine(local_day, datetime.time.min)
        for slot in get_available_slots(by_day.get(WEEKDAYS[local_day.weekday()], []), student_id):
            s = datetime.time.fromisoformat(slot["start"]) if slot["start"] != "24:00:00" else None
            e = datetime.time.fromisoformat(slot["end"]) if slot["end"] != "24:00:00" else None
            w_start = datetime.datetime.combine(local_day, s) if s else midnight + datetime.timedelta(days=1)
            w_end = datetime.datetime.combine(local_day, e) if e else midnight + datetime.timedelta(days=1)
            w_start, w_end = from_local(w_start, offset_hours), from_local(w_end, offset_hours)
            w_start, w_end = max(w_start, start), min(w_end, end)
            if w_start < w_end:
                windows.append({"start": w_start.isoformat(), "end": w_end.isoformat()})
        local_day += datetime.timedelta(days=1)
    return windows


def absence_block(tutor_settings: dict) -> list[dict]:
    """Период отпуска/болезни репетитора как занятый блок (если задан)."""
    start, end = tutor_settings.get("absence_from"), tutor_settings.get("absence_to")
    if not tutor_settings.get("absence_status") or not start or not end:
        return []
    return [{"start": _dt(start).isoformat(), "end": _dt(end).isoformat()}]


async def free_windows(db, *, tutor_id: int, student_id: int, tutor_settings: dict,
                       start: datetime.datetime, end: datetime.datetime) -> list[dict]:
    """Свободные для ученика окна репетитора в UTC на [start, end)."""
    bookings = await db.query('SELECT * FROM "bookings" WHERE tutor_id = :tid', {"tid": tutor_id})
    windows = booking_windows_utc(bookings, student_id, tutor_settings.get("timezone_offset"), start, end)
    if not windows:
        return []

    busy = absence_block(tutor_settings)
    lessons = await db.query(
        'SELECT id, tutor_id, start_time, end_time, status FROM "lessons" '
        'WHERE start_time < :de AND end_time > :ds',
        {"ds": start, "de": end},
    )
    mine = {
        p["lesson_id"]
        for p in await db.query('SELECT * FROM "lesson_participants" WHERE student_id = :sid', {"sid": student_id})
        if not is_cancelled_row(p)
    }
    for lesson in lessons:
        status = lesson.get("status") or "SCHEDULED"
        # Своя заявка, ждущая подтверждения, занимает время самого ученика
        # (не подать две заявки на одно время), но не время других учеников.
        own_pending = status == "PENDING" and lesson["id"] in mine
        if status in NON_BLOCKING_LESSON_STATUSES and not own_pending:
            continue
        # Занимают время урока репетитора (любой ученик) и собственные уроки ученика.
        if lesson["tutor_id"] == tutor_id or lesson["id"] in mine:
            busy.append({"start": _dt(lesson["start_time"]).isoformat(), "end": _dt(lesson["end_time"]).isoformat()})
    return subtract_blocks(windows, busy) if busy else windows
