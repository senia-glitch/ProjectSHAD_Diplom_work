# Тесты валидации дня недели в бронях репетитора.
# Запуск: pytest tests/test_weekday_validation.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core import ValidationError
from core.utils.security import create_access_token
from app.utils.bookings import validate_weekday, WEEKDAY_NAMES
from app.scenarios.tutor.bookings import (
    TutorCreateBookingDTO,
    TutorCreateBookingScenario,
    TutorUpdateBookingDTO,
    TutorUpdateBookingScenario,
)


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.tutors = {7: 42}
        self.bookings = {}
        self._next = 100

    async def query(self, sql, params, **kwargs):
        if '"tutors"' in sql:
            return [{"id": 42}] if params.get("uid") in self.tutors else []
        if '"configurations"' in sql:
            return []
        if '"bookings"' in sql:
            bid = params.get("bid")
            if bid is not None:
                row = self.bookings.get(bid)
                return [dict(row)] if row else []
            return []
        return []

    async def create(self, table, data, **kwargs):
        if table == "bookings":
            self._next += 1
            row = {"id": self._next, **data}
            self.bookings[row["id"]] = row
            return dict(row)
        raise AssertionError(table)

    async def read(self, table, rid, **kwargs):
        raise AssertionError(table)

    async def update(self, table, rid, data, **kwargs):
        raise AssertionError(table)

    async def delete(self, table, rid, **kwargs):
        raise AssertionError(table)


def test_validate_weekday_accepts_all_names():
    for name in WEEKDAY_NAMES:
        validate_weekday(name)


def test_validate_weekday_rejects_garbage():
    with pytest.raises(ValidationError):
        validate_weekday("FUNDAY")
    with pytest.raises(ValidationError):
        validate_weekday("monday")
    with pytest.raises(ValidationError):
        validate_weekday("")


def test_create_booking_rejects_invalid_weekday():
    db = StubDB()
    sc = TutorCreateBookingScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorCreateBookingDTO(
            access_token=create_access_token(7, "tutor"),
            weekday="FUNDAY", start_time="10:00", end_time="11:00",
        )))


def test_create_booking_accepts_valid_weekday():
    db = StubDB()
    sc = TutorCreateBookingScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(TutorCreateBookingDTO(
        access_token=create_access_token(7, "tutor"),
        weekday="MONDAY", start_time="10:00", end_time="11:00",
    )))
    assert res.booking_id
    assert db.bookings[res.booking_id]["weekday"] == "MONDAY"


def test_update_booking_rejects_invalid_weekday():
    db = StubDB()
    db.bookings[1] = {
        "id": 1, "tutor_id": 42, "weekday": "MONDAY",
        "start_time": datetime.time(10, 0), "end_time": datetime.time(11, 0),
        "access_rule": "EVERYONE", "access_targets": None,
    }
    sc = TutorUpdateBookingScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorUpdateBookingDTO(
            access_token=create_access_token(7, "tutor"),
            booking_id=1, weekday="FUNDAY",
        )))