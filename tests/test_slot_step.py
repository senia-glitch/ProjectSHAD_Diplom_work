# Тесты шага записи (slot_step_minutes): старт урока должен быть
# выровнен по шагу от начала окна доступности.
# Запуск: pytest tests/test_slot_step.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core import ValidationError
from core.utils.security import create_access_token
from app.utils.lessons import check_slot_availability
from app.scenarios.student.lessons import (
    StudentCreateLessonDTO,
    StudentCreateLessonScenario,
)
from tests.test_price_snapshot import StubDB, seed_pair, dt, iso, WEEKDAYS


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


def test_availability_requires_alignment_to_step():
    slots = [{"start": "2030-06-01T08:00:00", "end": "2030-06-01T18:00:00"}]
    assert check_slot_availability(dt(1, 10), dt(1, 11), slots, 60)
    assert not check_slot_availability(dt(1, 10, 15), dt(1, 11, 15), slots, 60)
    assert not check_slot_availability(dt(1, 10, 45), dt(1, 11, 45), slots, 90)
    assert check_slot_availability(dt(1, 9, 30), dt(1, 11), slots, 90)


def test_availability_without_step_unchanged():
    slots = [{"start": "2030-06-01T08:00:00", "end": "2030-06-01T18:00:00"}]
    assert check_slot_availability(dt(1, 10, 15), dt(1, 11, 15), slots)


def test_student_create_rejects_off_step_start():
    db = StubDB()
    seed_pair(db, rate=1500, discount=0)
    db.configs[0]["slot_step_minutes"] = 30
    day = dt(4, 10)
    db.bookings.append({
        "id": 1, "tutor_id": 42, "weekday": WEEKDAYS[day.weekday()],
        "start_time": datetime.time(8, 0), "end_time": datetime.time(18, 0),
        "access_rule": "EVERYONE", "access_targets": None,
    })
    sc = StudentCreateLessonScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(StudentCreateLessonDTO(
            access_token=create_access_token(11, "student"), tutor_user_id=7,
            start_time=iso(4, 10, 15), end_time=iso(4, 11, 15),
        )))


def test_student_create_accepts_aligned_start():
    db = StubDB()
    seed_pair(db, rate=1500, discount=0)
    db.configs[0]["slot_step_minutes"] = 30
    day = dt(4, 10)
    db.bookings.append({
        "id": 1, "tutor_id": 42, "weekday": WEEKDAYS[day.weekday()],
        "start_time": datetime.time(8, 0), "end_time": datetime.time(18, 0),
        "access_rule": "EVERYONE", "access_targets": None,
    })
    sc = StudentCreateLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentCreateLessonDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7,
        start_time=iso(4, 10, 30), end_time=iso(4, 11, 30),
    )))
    assert res.lesson_id