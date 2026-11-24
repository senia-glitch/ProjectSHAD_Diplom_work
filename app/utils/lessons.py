"""Чистая бизнес-логика уроков. Без IO-зависимостей."""

from app.utils.clock import utc_now, to_utc_naive
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
# PENDING — заявка ученика ждёт подтверждения репетитора (время не занимает);
# REJECTED — заявка отклонена (репетитором или системой);
# SYSTEM_FINISHED — урок пришёлся на отпуск/болезнь и закрыт системой
# (в оплатах и статистике как проведённый не учитывается).
# FINISHED/CANCELLED/NO_SHOW/REJECTED/SYSTEM_FINISHED терминальны.
LESSON_STATUS_PENDING = "PENDING"
LESSON_STATUS_SCHEDULED = "SCHEDULED"
LESSON_STATUS_ONGOING = "ONGOING"
LESSON_STATUS_FINISHED = "FINISHED"
LESSON_STATUS_CANCELLED = "CANCELLED"
LESSON_STATUS_NO_SHOW = "NO_SHOW"
LESSON_STATUS_REJECTED = "REJECTED"
LESSON_STATUS_SYSTEM_FINISHED = "SYSTEM_FINISHED"

LESSON_STATUSES = frozenset({
    LESSON_STATUS_PENDING,
    LESSON_STATUS_SCHEDULED,
    LESSON_STATUS_ONGOING,
    LESSON_STATUS_FINISHED,
    LESSON_STATUS_CANCELLED,
    LESSON_STATUS_NO_SHOW,
    LESSON_STATUS_REJECTED,
    LESSON_STATUS_SYSTEM_FINISHED,
})

TERMINAL_LESSON_STATUSES = frozenset({
    LESSON_STATUS_FINISHED,
    LESSON_STATUS_CANCELLED,
    LESSON_STATUS_NO_SHOW,
    LESSON_STATUS_REJECTED,
    LESSON_STATUS_SYSTEM_FINISHED,
})

# Не занимают время репетитора и ученика.
NON_BLOCKING_LESSON_STATUSES = frozenset({
    LESSON_STATUS_PENDING,
    LESSON_STATUS_CANCELLED,
    LESSON_STATUS_REJECTED,
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
    if current == LESSON_STATUS_PENDING:
        # Заявку без ответа к началу урока отклоняет система
        # (фоновая задача записывает это в историю статусов).
        return LESSON_STATUS_REJECTED if now >= start_time else None
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
        now = utc_now()
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
    """Урок целиком внутри одного непрерывного свободного окна и стоит по шагу
    от начала этого окна. Смежные окна (например, разрезанные полуночью
    в поясе репетитора) склеиваются: полночь UTC окно не режет."""
    from app.utils.safe_parse import parse_iso_datetime

    intervals = sorted(
        (parse_iso_datetime(s["start"], "slot.start"), parse_iso_datetime(s["end"], "slot.end"))
        for s in free_slots
    )
    merged: list[list[datetime.datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    for start, end in merged:
        if start <= requested_start and requested_end <= end:
            if step_minutes and step_minutes > 0:
                offset = int((requested_start - start).total_seconds() // 60)
                return offset % step_minutes == 0
            return True
    return False


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


STATUS_ACTORS = frozenset({"system", "tutor", "student"})
MAX_REASON_LENGTH = 500


def status_event(
    status: str,
    by: str,
    *,
    actor_user_id: int | None = None,
    reason: str | None = None,
    meta: dict | None = None,
    at: datetime.datetime | None = None,
) -> dict:
    """Запись истории статуса урока: кто (система/репетитор/ученик), когда, почему."""
    if by not in STATUS_ACTORS:
        raise ValueError(f"Unknown status actor: {by}")
    event = {
        "status": status,
        "by": by,
        "actor_user_id": actor_user_id,
        "at": (at or utc_now()).replace(microsecond=0).isoformat(),
    }
    reason = (reason or "").strip()
    if reason:
        event["reason"] = reason[:MAX_REASON_LENGTH]
    if meta:
        event["meta"] = meta
    return event


def with_status_event(history, event: dict) -> list:
    """Новая история с добавленным событием (исходный список не меняется)."""
    return [*(history if isinstance(history, list) else []), event]


def last_status_event(history, statuses=None) -> dict | None:
    """Последнее событие (опционально — только среди указанных статусов)."""
    for event in reversed(history if isinstance(history, list) else []):
        if isinstance(event, dict) and (statuses is None or event.get("status") in statuses):
            return event
    return None
