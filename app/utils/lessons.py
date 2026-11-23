"""Чистая бизнес-логика уроков. Без IO-зависимостей."""

import asyncio
import datetime
from core import ConflictError, ValidationError


MAX_LESSON_DURATION_MINUTES = 10080  # 168 часов = 1 неделя

# Сериализация scheduling-операций одного репетитора внутри процесса.
# check-then-create/update не атомарен (в lessons нет констрейнта пересечений),
# поэтому конкурентные создания/переносы lessons serialize per tutor_id.
# В деплое FAT_WORKERS=1 покрывает все конкурентные запросы.
_lesson_locks: dict[int, asyncio.Lock] = {}
_lesson_locks_guard = asyncio.Lock()


async def tutor_schedule_lock(tutor_id: int) -> asyncio.Lock:
    """Лок расписание-операций репетитора (создание/перенос уроков)."""
    async with _lesson_locks_guard:
        lock = _lesson_locks.get(tutor_id)
        if lock is None:
            lock = asyncio.Lock()
            _lesson_locks[tutor_id] = lock
        return lock


# Статусы урока. SCHEDULED/ONGOING/FINISHED двигает только время
# (resolve_lesson_status), CANCELLED/NO_SHOW ставит репетитор вручную.
# FINISHED/CANCELLED/NO_SHOW терминальны: время их не меняет.
LESSON_STATUS_SCHEDULED = "SCHEDULED"
LESSON_STATUS_ONGOING = "ONGOING"
LESSON_STATUS_FINISHED = "FINISHED"
LESSON_STATUS_CANCELLED = "CANCELLED"
LESSON_STATUS_NO_SHOW = "NO_SHOW"

LESSON_STATUSES = frozenset({
    LESSON_STATUS_SCHEDULED,
    LESSON_STATUS_ONGOING,
    LESSON_STATUS_FINISHED,
    LESSON_STATUS_CANCELLED,
    LESSON_STATUS_NO_SHOW,
})

TERMINAL_LESSON_STATUSES = frozenset({
    LESSON_STATUS_FINISHED,
    LESSON_STATUS_CANCELLED,
    LESSON_STATUS_NO_SHOW,
})

MANUAL_LESSON_STATUSES = frozenset({
    LESSON_STATUS_FINISHED,
    LESSON_STATUS_CANCELLED,
    LESSON_STATUS_NO_SHOW,
})


def check_lesson_overlap(overlapping_lessons: list) -> None:
    """Сторож пересечений: урок репетитора не должен пересекаться
    с его существующими уроками. Зеркалит check_booking_overlap:
    факт пересечения определяет SQL-запрос, здесь только решение."""
    if overlapping_lessons:
        raise ConflictError("Lesson overlaps with an existing one")


def resolve_effective_interval(
    existing_start: datetime.datetime,
    existing_end: datetime.datetime,
    new_start: datetime.datetime | None = None,
    new_end: datetime.datetime | None = None,
) -> tuple[datetime.datetime, datetime.datetime, bool]:
    """Эффективный интервал урока после правки и флаг изменения времени."""
    start = new_start if new_start is not None else existing_start
    end = new_end if new_end is not None else existing_end
    changed = new_start is not None or new_end is not None
    return start, end, changed


def resolve_lesson_status(
    current: str | None,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    now: datetime.datetime,
) -> str | None:
    """Новый статус по серверному времени или None (менять не надо)."""
    current = current or LESSON_STATUS_SCHEDULED
    if current in TERMINAL_LESSON_STATUSES:
        return None
    if now >= end_time:
        return LESSON_STATUS_FINISHED
    if now >= start_time:
        return LESSON_STATUS_ONGOING
    return LESSON_STATUS_SCHEDULED


def validate_lesson_times(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    *,
    now: datetime.datetime | None = None,
) -> None:
    if start_time >= end_time:
        raise ValidationError("start_time must be less than end_time")
    duration = end_time - start_time
    if duration.total_seconds() / 60 > MAX_LESSON_DURATION_MINUTES:
        raise ValidationError(f"Lesson duration cannot exceed {MAX_LESSON_DURATION_MINUTES} minutes (168 hours)")
    if now is None:
        now = datetime.datetime.now()
    if start_time < now:
        raise ValidationError("Cannot create lesson in the past")


def validate_booking_lead_time(
    now: datetime.datetime,
    start_time: datetime.datetime,
    lead_hours: int,
) -> None:
    earliest = now + datetime.timedelta(hours=lead_hours)
    if start_time < earliest:
        raise ValidationError(f"Lesson must be booked at least {lead_hours}h in advance")


def check_slot_availability(
    requested_start: datetime.datetime,
    requested_end: datetime.datetime,
    free_slots: list[dict],
    step_minutes: int | None = None,
) -> bool:
    from app.utils.safe_parse import parse_iso_datetime

    current = requested_start
    while current < requested_end:
        next_day = current.date() + datetime.timedelta(days=1)
        day_end = datetime.datetime.combine(next_day, datetime.time.min)
        piece_end = min(requested_end, day_end)

        piece_slot = None
        for s in free_slots:
            slot_start = parse_iso_datetime(s["start"], "slot.start")
            slot_end = parse_iso_datetime(s["end"], "slot.end")
            if slot_start <= current and slot_end >= piece_end:
                piece_slot = (slot_start, slot_end)
                break

        if piece_slot is None:
            return False

        if step_minutes and step_minutes > 0:
            offset = int((current - piece_slot[0]).total_seconds() // 60)
            if offset % step_minutes != 0:
                return False

        current = day_end

    return True


def build_lesson_create_data(
    tutor_id: int,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    created_by_id: int,
    *,
    is_group: bool = False,
    lesson_descriptions: str | None = None,
    lesson_settings: dict | None = None,
    lesson_links: list[dict] | None = None,
    lesson_metadata: dict | None = None,
) -> dict:
    data = {
        "tutor_id": tutor_id,
        "start_time": start_time,
        "end_time": end_time,
        "created_by_id": created_by_id,
        "is_group": is_group,
    }
    if lesson_descriptions is not None:
        data["lesson_descriptions"] = lesson_descriptions
    if lesson_settings is not None:
        data["lesson_settings"] = lesson_settings
    if lesson_links is not None:
        data["lesson_links"] = lesson_links
    if lesson_metadata is not None:
        data["lesson_metadata"] = lesson_metadata
    return data


def build_lesson_update_data(dto_fields: dict) -> dict:
    from app.utils.safe_parse import parse_iso_datetime

    result = {}
    time_fields = {"start_time", "end_time"}
    for k, v in dto_fields.items():
        if v is not None:
            if k in time_fields and isinstance(v, str):
                result[k] = parse_iso_datetime(v, k)
            else:
                result[k] = v
    return result
