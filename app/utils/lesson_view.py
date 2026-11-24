"""Пометки урока для показа: история статусов и период отсутствия репетитора. Без IO."""
import datetime

from app.utils.clock import to_utc_naive
from app.utils.json_codec import parse_value
from app.utils.lessons import last_status_event
from app.utils.participants import cancellation_of

NOTE_STATUSES = ("PENDING", "CANCELLED", "REJECTED", "SYSTEM_FINISHED")


def _dt(value) -> datetime.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return to_utc_naive(value)
    return datetime.datetime.fromisoformat(str(value).replace(" ", "T"))


def status_history(lesson: dict) -> list[dict]:
    history = parse_value(lesson.get("status_history"), "list") or []
    return [e for e in history if isinstance(e, dict)]


def status_note(lesson: dict, participant: dict | None = None) -> dict | None:
    """Последнее значимое событие урока (кто/когда/почему) для текущего статуса.

    Для ученика, вышедшего из группового урока, пометкой служит его собственная
    отмена записи: урок продолжается без него.
    """
    status = lesson.get("status") or "SCHEDULED"
    if participant is not None:
        mark = cancellation_of(parse_value(participant.get("participant_settings"), "dict"))
        if mark and status not in ("CANCELLED", "REJECTED"):
            return {"status": "CANCELLED", "scope": "participant", **mark}
    if status not in NOTE_STATUSES:
        return None
    event = last_status_event(status_history(lesson), {status})
    return dict(event) if event else {"status": status, "by": None}


def personal_status(lesson: dict, participant: dict | None) -> str:
    """Статус урока глазами ученика: вышедшему из группового урока он отменён."""
    status = lesson.get("status") or "SCHEDULED"
    if participant is not None and cancellation_of(parse_value(participant.get("participant_settings"), "dict")):
        return "CANCELLED"
    return status


def absence_note(lesson: dict, tutor_settings: dict | None) -> dict | None:
    """Период отпуска/болезни, на который пришёлся урок (урок заморожен, не отменён)."""
    if not tutor_settings or not tutor_settings.get("absence_status"):
        return None
    start, end = _dt(tutor_settings.get("absence_from")), _dt(tutor_settings.get("absence_to"))
    lesson_start, lesson_end = _dt(lesson.get("start_time")), _dt(lesson.get("end_time"))
    if not (start and end and lesson_start and lesson_end):
        return None
    if lesson_start < end and lesson_end > start:
        return {
            "status": tutor_settings["absence_status"],
            "from": start.isoformat(),
            "to": end.isoformat(),
        }
    return None
