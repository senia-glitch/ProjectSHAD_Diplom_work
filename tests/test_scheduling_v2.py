# Доработки расписания: время в UTC и личные пояса, окна броней в поясе репетитора,
# обрезка окна по lead time (D2), отмена урока учеником (D1), история статусов,
# отпуск/болезнь с границами. Запуск: pytest tests/test_scheduling_v2.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ValidationError
from core.utils.security import create_access_token

from tests.test_price_snapshot import DummyMetrics, StubDB, seed_pair
from app.utils.clock import from_local, to_local, to_utc_naive, utc_now
from app.utils.lessons import (
    check_slot_availability,
    last_status_event,
    resolve_lesson_status,
    status_event,
    with_status_event,
)
from app.utils.lesson_view import absence_note, personal_status, status_note
from app.scenarios.student.availability import booking_windows_utc
from app.scenarios.student.tutors import (
    StudentGetAvailableSlotsDTO,
    StudentGetAvailableSlotsScenario,
    align_up,
)
from app.scenarios.student.lessons import StudentLeaveLessonDTO, StudentLeaveLessonScenario
from app.scenarios.tutor.profile import effective_work_status
from app.utils.safe_parse import parse_range

D = datetime.datetime


def run(coro):
    return asyncio.run(coro)


def booking(weekday, start, end, rule="EVERYONE", targets=None):
    return {"tutor_id": 42, "weekday": weekday, "start_time": start, "end_time": end,
            "access_rule": rule, "access_targets": targets}


# --- часы и пояса ---


def test_clock_is_utc_and_offsets_are_display_only():
    now = utc_now()
    assert now.tzinfo is None
    assert abs((datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - now).total_seconds()) < 5
    moment = D(2030, 6, 5, 22, 0)
    assert to_local(moment, 8) == D(2030, 6, 6, 6, 0)
    assert from_local(to_local(moment, -5), -5) == moment
    aware = datetime.datetime(2030, 1, 1, 12, tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
    assert to_utc_naive(aware) == D(2030, 1, 1, 9, 0)


def test_parse_range_accepts_utc_datetimes_and_plain_dates():
    assert parse_range("2030-06-03", "2030-06-09") == (D(2030, 6, 3), D(2030, 6, 10))
    # Местная неделя пользователя UTC+8 приходит границами в UTC.
    assert parse_range("2030-06-02T16:00:00", "2030-06-09T16:00:00") == (D(2030, 6, 2, 16), D(2030, 6, 9, 16))
    with pytest.raises(ValidationError):
        parse_range("2030-06-09", "2030-06-03")


# --- окна броней в поясе репетитора ---


def test_booking_windows_follow_tutor_timezone():
    # Репетитор в UTC+8: бронь Ср 10:00–14:00 по его часам = Ср 02:00–06:00 UTC.
    rows = [booking("WEDNESDAY", datetime.time(10), datetime.time(14))]
    windows = booking_windows_utc(rows, 5, 8, D(2030, 6, 3), D(2030, 6, 10))
    assert windows == [{"start": "2030-06-05T02:00:00", "end": "2030-06-05T06:00:00"}]


def test_booking_window_crossing_utc_midnight_is_one_window():
    # Репетитор в UTC+8, бронь Ср 06:00–10:00 местного = Вт 22:00 – Ср 02:00 UTC.
    rows = [booking("WEDNESDAY", datetime.time(6), datetime.time(10))]
    windows = booking_windows_utc(rows, 5, 8, D(2030, 6, 3), D(2030, 6, 10))
    assert windows == [{"start": "2030-06-04T22:00:00", "end": "2030-06-05T02:00:00"}]
    # Урок через полночь UTC внутри этого окна допустим и стоит по шагу.
    assert check_slot_availability(D(2030, 6, 4, 23), D(2030, 6, 5, 1), windows, 60)
    assert not check_slot_availability(D(2030, 6, 4, 22, 30), D(2030, 6, 4, 23, 30), windows, 60)


def test_access_rules_still_filter_windows():
    rows = [booking("WEDNESDAY", datetime.time(10), datetime.time(12), "ONLY", [9]),
            booking("WEDNESDAY", datetime.time(14), datetime.time(16), "ALL_EXCEPT", [9]),
            booking("WEDNESDAY", datetime.time(18), datetime.time(20), "NOBODY")]
    for_5 = booking_windows_utc(rows, 5, 0, D(2030, 6, 5), D(2030, 6, 6))
    for_9 = booking_windows_utc(rows, 9, 0, D(2030, 6, 5), D(2030, 6, 6))
    assert [w["start"][11:16] for w in for_5] == ["14:00"]
    assert [w["start"][11:16] for w in for_9] == ["10:00"]


def test_adjacent_windows_merge_for_step_check():
    windows = [{"start": "2030-06-05T10:00:00", "end": "2030-06-05T12:00:00"},
               {"start": "2030-06-05T12:00:00", "end": "2030-06-05T14:00:00"}]
    assert check_slot_availability(D(2030, 6, 5, 11), D(2030, 6, 5, 13), windows, 60)
    assert not check_slot_availability(D(2030, 6, 5, 13), D(2030, 6, 5, 15), windows, 60)


# --- D2: окно, пересекающее границу lead time ---


def test_align_up_counts_steps_from_window_start():
    start = D(2030, 6, 5, 0, 0)
    assert align_up(start, D(2030, 6, 5, 3, 10), 60) == D(2030, 6, 5, 4, 0)
    assert align_up(start, D(2030, 6, 5, 4, 0), 60) == D(2030, 6, 5, 4, 0)
    assert align_up(D(2030, 6, 5, 0, 30), D(2030, 6, 5, 1, 0), 45) == D(2030, 6, 5, 1, 15)


def test_slots_keep_allowed_part_of_window_crossing_lead_time():
    """Бронь 00:00–06:00, сейчас+24 ч попадает внутрь: доступна часть с ближайшего шага, не копия другого окна."""
    db = StubDB()
    seed_pair(db)
    db.tutor_settings[42]["timezone_offset"] = 0
    db.configs[0].update({"booking_lead_time_hours": 24, "slot_step_minutes": 60})
    earliest = utc_now() + datetime.timedelta(hours=24)
    day = earliest.date()
    weekday = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"][day.weekday()]
    db.bookings.append(booking(weekday, datetime.time(0), datetime.time(23, 0)))
    res = run(StudentGetAvailableSlotsScenario(db=db, metrics=DummyMetrics()).execute(
        StudentGetAvailableSlotsDTO(
            access_token=create_access_token(11, "student"), tutor_user_id=7,
            date_from=day.isoformat(), date_to=day.isoformat(),
        )))
    if earliest.hour >= 22:  # граница после последнего начала — окна на этот день нет
        assert res.slots == []
        return
    assert len(res.slots) == 1
    first = D.fromisoformat(res.slots[0].start)
    assert first >= earliest and (first - earliest) < datetime.timedelta(hours=1)
    assert first.minute == 0
    assert res.slots[0].end == f"{day.isoformat()}T23:00:00"


# --- история статусов и пометки урока ---


def test_status_event_records_actor_time_reason():
    event = status_event("CANCELLED", "student", actor_user_id=11, reason="  заболел  ",
                         at=D(2030, 6, 1, 9, 0, 0, 500))
    assert event == {"status": "CANCELLED", "by": "student", "actor_user_id": 11,
                     "at": "2030-06-01T09:00:00", "reason": "заболел"}
    with pytest.raises(ValueError):
        status_event("CANCELLED", "admin")
    history = with_status_event(None, status_event("SCHEDULED", "tutor", actor_user_id=7))
    history = with_status_event(history, event)
    assert last_status_event(history, {"CANCELLED"})["reason"] == "заболел"
    assert last_status_event(history)["status"] == "CANCELLED"


def test_status_note_uses_history_and_participant_mark():
    lesson = {"status": "REJECTED", "status_history": [
        status_event("PENDING", "student", actor_user_id=11),
        status_event("REJECTED", "system", reason="Репетитор не ответил"),
    ]}
    assert status_note(lesson)["by"] == "system"
    group = {"status": "SCHEDULED", "status_history": []}
    left = {"participant_settings": {"cancelled": {"by": "student", "at": "x"}}}
    assert status_note(group, left)["scope"] == "participant"
    assert personal_status(group, left) == "CANCELLED"
    assert status_note({"status": "SCHEDULED"}) is None


def test_pending_request_expires_at_start():
    start = D(2030, 6, 5, 10)
    assert resolve_lesson_status("PENDING", start, start + datetime.timedelta(hours=1), start - datetime.timedelta(minutes=1)) is None
    assert resolve_lesson_status("PENDING", start, start + datetime.timedelta(hours=1), start) == "REJECTED"
    assert resolve_lesson_status("REJECTED", start, start + datetime.timedelta(hours=1), start) is None


# --- отпуск/болезнь ---


def test_absence_marks_lessons_and_work_status_by_period():
    settings = {"absence_status": "VACATION", "absence_from": "2030-06-01T00:00:00",
                "absence_to": "2030-06-10T00:00:00"}
    inside = {"start_time": "2030-06-05T10:00:00", "end_time": "2030-06-05T11:00:00"}
    outside = {"start_time": "2030-06-12T10:00:00", "end_time": "2030-06-12T11:00:00"}
    assert absence_note(inside, settings)["status"] == "VACATION"
    assert absence_note(outside, settings) is None
    assert effective_work_status(settings, now=D(2030, 6, 5)) == "VACATION"
    assert effective_work_status(settings, now=D(2030, 5, 30)) == "WORKING"
    assert effective_work_status({"absence_status": None}) == "WORKING"


# --- D1: ученик отменяет урок ---


class LeaveStub(StubDB):
    async def update(self, table, rid, data):
        if table == "lesson_participants":
            self.participants[rid].update(data)
            return dict(self.participants[rid])
        return await super().update(table, rid, data)

    async def query(self, sql, params):
        if '"lesson_participants"' in sql and "student_id != :sid" in sql:
            return [dict(p) for p in self.participants.values()
                    if p["lesson_id"] == params["lid"] and p["student_id"] != params["sid"]]
        if '"users"' in sql:
            return [{"full_name": "Илья"}]
        return await super().query(sql, params)


def leave_db(hours_ahead, lead=24, status="SCHEDULED"):
    db = LeaveStub()
    seed_pair(db)
    db.configs[0]["cancellation_lead_time_hours"] = lead
    start = utc_now().replace(microsecond=0) + datetime.timedelta(hours=hours_ahead)
    db.lessons[1] = {"id": 1, "tutor_id": 42, "start_time": start,
                     "end_time": start + datetime.timedelta(hours=1), "is_group": False,
                     "status": status, "status_history": None}
    db.participants[1] = {"id": 1, "lesson_id": 1, "student_id": 5, "participant_settings": {}}
    return db


def leave(db, reason=None):
    return run(StudentLeaveLessonScenario(db=db, metrics=DummyMetrics()).execute(
        StudentLeaveLessonDTO(access_token=create_access_token(11, "student"), lesson_id=1, reason=reason)))


def test_student_cancels_individual_lesson_before_deadline():
    db = leave_db(48)
    assert leave(db, "уезжаю").ok
    lesson = db.lessons[1]
    assert lesson["status"] == "CANCELLED"
    history = lesson["status_history"]
    history = history if isinstance(history, list) else __import__("json").loads(history)
    assert history[-1]["by"] == "student" and history[-1]["reason"] == "уезжаю"
    mark = db.participants[1]["participant_settings"]
    mark = mark if isinstance(mark, dict) else __import__("json").loads(mark)
    assert mark["cancelled"]["by"] == "student" and mark["cancelled"]["actor_user_id"] == 11
    # Повторная отмена — идемпотентный ok.
    assert leave(db).ok


def test_student_cannot_cancel_after_deadline():
    db = leave_db(10, lead=24)
    with pytest.raises(ValidationError):
        leave(db)
    assert db.lessons[1]["status"] == "SCHEDULED"


def test_student_can_withdraw_pending_request_any_time():
    db = leave_db(2, lead=24, status="PENDING")
    assert leave(db).ok
    assert db.lessons[1]["status"] == "CANCELLED"
