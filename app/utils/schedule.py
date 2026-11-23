"""Утилиты для работы с расписанием. Чистая логика без IO."""

import datetime
from typing import List, Dict

from app.utils.json_codec import parse_int_list


def get_available_slots(
    bookings: List[Dict],
    student_id: int,
    day_start: str = "00:00",
    day_end: str = "24:00",
) -> List[Dict[str, str]]:
    allowing = []
    for b in bookings:
        if _is_available_for_student(b, student_id):
            allowing.append(b)

    if not allowing:
        return []

    allowing.sort(key=lambda b: _to_time(b["start_time"]))

    merged = []
    current_start = _to_time(allowing[0]["start_time"])
    current_end = _to_time(allowing[0]["end_time"])

    for b in allowing[1:]:
        b_start = _to_time(b["start_time"])
        b_end = _to_time(b["end_time"])

        if b_start <= current_end:
            if b_end > current_end:
                current_end = b_end
        else:
            merged.append({"start": _to_str(current_start), "end": _to_str(current_end)})
            current_start = b_start
            current_end = b_end

    merged.append({"start": _to_str(current_start), "end": _to_str(current_end)})

    day_start_time = _to_time(day_start)
    day_end_time = _to_time(day_end)

    slots = []
    for m in merged:
        start = max(_to_time(m["start"]), day_start_time)
        end = min(_to_time(m["end"]), day_end_time)
        if start < end:
            slots.append({"start": _to_str(start), "end": _to_str(end)})

    return slots


def _is_available_for_student(booking: Dict, student_id: int) -> bool:
    rule = booking.get("access_rule", "EVERYONE")
    # Единый кодек: всегда list[int], даже если из БД пришла str/None/мусор.
    targets = parse_int_list(booking.get("access_targets"))

    if rule == "EVERYONE":
        return True
    if rule == "ONLY":
        return student_id in targets
    if rule == "ALL_EXCEPT":
        return student_id not in targets
    if rule == "NOBODY":
        return False
    return False


def merge_lessons(
    student_lessons: List[Dict],
    tutor_lessons: List[Dict],
) -> List[Dict[str, str]]:
    all_lessons = list(student_lessons) + list(tutor_lessons)
    if not all_lessons:
        return []

    all_lessons.sort(key=lambda x: _to_dt(x["start_time"]))

    merged = []
    current_start = _to_dt(all_lessons[0]["start_time"])
    current_end = _to_dt(all_lessons[0]["end_time"])

    for lesson in all_lessons[1:]:
        l_start = _to_dt(lesson["start_time"])
        l_end = _to_dt(lesson["end_time"])

        if l_start < current_end:
            if l_end > current_end:
                current_end = l_end
        else:
            merged.append({"start": _to_dt_str(current_start), "end": _to_dt_str(current_end)})
            current_start = l_start
            current_end = l_end

    merged.append({"start": _to_dt_str(current_start), "end": _to_dt_str(current_end)})
    return merged


def subtract_blocks(
    available_slots: List[Dict[str, str]],
    busy_blocks: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    if not busy_blocks:
        return available_slots

    result = []
    for slot in available_slots:
        slot_start = _to_dt(slot["start"])
        slot_end = _to_dt(slot["end"])

        pieces = [(slot_start, slot_end)]
        for block in busy_blocks:
            block_start = _to_dt(block["start"])
            block_end = _to_dt(block["end"])

            new_pieces = []
            for piece_start, piece_end in pieces:
                if piece_end <= block_start or piece_start >= block_end:
                    new_pieces.append((piece_start, piece_end))
                else:
                    if piece_start < block_start:
                        new_pieces.append((piece_start, block_start))
                    if piece_end > block_end:
                        new_pieces.append((block_end, piece_end))
            pieces = new_pieces

        for piece_start, piece_end in pieces:
            result.append({
                "start": _to_dt_str(piece_start),
                "end": _to_dt_str(piece_end),
            })

    return result


def _to_time(value):
    from core import ValidationError

    if isinstance(value, datetime.time):
        return value
    if isinstance(value, datetime.datetime):
        return value.time()
    s = str(value)
    if s in ("24:00", "24:00:00"):
        return datetime.time.max
    try:
        if "T" in s or " " in s:
            return datetime.datetime.fromisoformat(s.replace(" ", "T")).time()
        return datetime.time.fromisoformat(s)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid time value: {value!r}")


def _to_dt(value) -> datetime.datetime:
    from core import ValidationError

    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.time):
        return datetime.datetime.combine(datetime.date.today(), value)
    s = str(value)
    try:
        if "T" in s or " " in s:
            return datetime.datetime.fromisoformat(s.replace(" ", "T"))
        t = _to_time(value)
        return datetime.datetime.combine(datetime.date.today(), t)
    except ValidationError:
        raise
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid datetime value: {value!r}")


def _to_str(value) -> str:
    if isinstance(value, datetime.time):
        if value == datetime.time.max:
            return "24:00:00"
        return value.strftime("%H:%M:%S")
    return str(value)


def _to_dt_str(value) -> str:
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.time):
        return datetime.datetime.combine(datetime.date.today(), value).isoformat()
    return str(value)
