# Тесты валидации дат в /tutor/students/{id}/busy-slots.
# Запуск: pytest tests/test_busy_slots_dates.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core import ValidationError
from core.utils.security import create_access_token
from app.scenarios.tutor.students import (
    TutorGetStudentBusySlotsDTO,
    TutorGetStudentBusySlotsScenario,
)


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.tutors = {7: 42}
        self.students = {11: 5}
        self.configs = [{"id": 77, "student_id": 5, "tutor_id": 42}]
        self.participants = {}
        self.lessons = {}

    async def query(self, sql, params, **kwargs):
        if '"tutors"' in sql:
            return [{"id": 42}] if params.get("uid") in self.tutors else []
        if '"students"' in sql:
            return [{"id": 5}] if params.get("uid") in self.students else []
        if '"configurations"' in sql:
            return [
                dict(c) for c in self.configs
                if c["student_id"] == params.get("sid") and c["tutor_id"] == params.get("tid")
            ]
        if '"lesson_participants"' in sql:
            sid = params.get("sid")
            return [dict(p) for p in self.participants.values() if p["student_id"] == sid]
        if '"lessons"' in sql:
            lid = params.get("lid")
            row = self.lessons.get(lid)
            return [dict(row)] if row else []
        return []


def test_busy_slots_rejects_garbage_date():
    db = StubDB()
    sc = TutorGetStudentBusySlotsScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorGetStudentBusySlotsDTO(
            access_token=create_access_token(7, "tutor"),
            student_user_id=11, date_from="garbage", date_to="2030-06-10",
        )))


def test_busy_slots_rejects_inverted_range():
    db = StubDB()
    sc = TutorGetStudentBusySlotsScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorGetStudentBusySlotsDTO(
            access_token=create_access_token(7, "tutor"),
            student_user_id=11, date_from="2030-06-20", date_to="2030-06-10",
        )))


def test_busy_slots_valid_range_ok():
    db = StubDB()
    db.lessons[1] = {
        "id": 1, "tutor_id": 42,
        "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11),
        "status": "SCHEDULED",
    }
    db.participants[501] = {
        "id": 501, "lesson_id": 1, "student_id": 5, "participant_settings": None,
    }
    sc = TutorGetStudentBusySlotsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(TutorGetStudentBusySlotsDTO(
        access_token=create_access_token(7, "tutor"),
        student_user_id=11, date_from="2030-05-01", date_to="2030-06-30",
    )))
    assert len(res.busy_slots) == 1