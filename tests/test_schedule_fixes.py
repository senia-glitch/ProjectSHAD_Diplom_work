# Тесты исправлений расписания: брони до 24:00 (БАГ 5), пересечение
# полуночи в слотах/занятости (БАГ 4/6) и сериализация создания уроков
# одним репетитором (БАГ 8). Запуск: pytest tests/test_schedule_fixes.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ValidationError
from core.utils.security import create_access_token

from tests.test_price_snapshot import StubDB, seed_pair, dt, iso, WEEKDAYS
from app.utils.json_codec import parse_row
from app.scenarios.student.lessons import StudentCreateLessonDTO, StudentCreateLessonScenario
from app.scenarios.student.tutors import StudentGetAvailableSlotsDTO, StudentGetAvailableSlotsScenario
from app.scenarios.tutor.bookings import TutorCreateBookingDTO, TutorCreateBookingScenario
from app.scenarios.tutor.students import TutorGetStudentBusySlotsDTO, TutorGetStudentBusySlotsScenario

TUE = WEEKDAYS[1]
WED = WEEKDAYS[2]


def run(coro):
    return asyncio.run(coro)


class M:
    async def record(self, *a, **k):
        return None


class ScheduleStub(StubDB):
    """StubDB + диапазонные/overlap-запросы к lessons + create броней.

    Время в бронях возвращает типом datetime.time (как realный PG), строки
   学员/snaptshot прогоняются через parse_row (имитация JSONB round-trip).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._next_booking = 10

    async def query(self, sql, params):
        if '"lessons"' in sql and ":et" in sql and ":st" in sql:
            out = []
            for l in self.lessons.values():
                if "tutor_id" in sql and l.get("tutor_id") != params.get("tid"):
                    continue
                if (l.get("status") or "SCHEDULED") == "CANCELLED":
                    continue
                if l["start_time"] < params["et"] and l["end_time"] > params["st"]:
                    out.append(dict(l))
            return out
        if '"lessons"' in sql and "start_time <= " in sql and "end_time >= " in sql:
            out = []
            for l in self.lessons.values():
                if "tutor_id" in sql and l.get("tutor_id") != params.get("tid"):
                    continue
                if (l.get("status") or "SCHEDULED") == "CANCELLED":
                    continue
                if l["start_time"] <= params["de"] and l["end_time"] >= params["ds"]:
                    out.append(dict(l))
            return out
        return await super().query(sql, params)

    async def create(self, table, data):
        if table == "bookings":
            self._next_booking += 1
            row = parse_row("bookings", {"id": self._next_booking, **data})
            self.bookings.append(row)
            return dict(row)
        return await super().create(table, data)


def make_db(*, rate=2000, discount=10):
    db = ScheduleStub()
    seed_pair(db, rate=rate, discount=discount)
    db.tutors[7] = 42
    # Второй ученик с конфигурацией к тому же репетитору (для теста гонки).
    db.students[99] = 6
    db.student_settings[6] = {"student_id": 6, "status": "ACTIVE"}
    db.configs.append({
        "id": 78, "student_id": 6, "tutor_id": 42,
        "hourly_rate": rate, "discount": discount,
        "allow_self_booking": True, "booking_lead_time_hours": 0,
        "default_links": None,
    })
    db.configs[0]["slot_step_minutes"] = 60
    db.configs[0]["booking_lead_time_hours"] = 0
    return db


def add_booking(db, booking_id, weekday, start: datetime.time, end: datetime.time):
    db.bookings.append({
        "id": booking_id, "tutor_id": 42, "weekday": weekday,
        "start_time": start, "end_time": end,
        "access_rule": "EVERYONE", "access_targets": None,
    })


# ---套餐 5: бронь "до 24:00" и полуночные уроки ---


def test_booking_end_24_00_is_stored_as_end_of_day():
    db = make_db()
    sc = TutorCreateBookingScenario(db=db, metrics=M())
    res = run(sc.execute(TutorCreateBookingDTO(
        access_token=create_access_token(7, "tutor"),
        weekday=TUE, start_time="08:00", end_time="24:00",
    )))
    assert res.booking_id
    stored = next(b for b in db.bookings if b["id"] == res.booking_id)
    assert stored["end_time"] == datetime.time.max


def test_student_can_book_lesson_ending_exactly_at_midnight():
    db = make_db()
    add_booking(db, 1, TUE, datetime.time(8, 0), datetime.time.max)
    sc = StudentCreateLessonScenario(db=db, metrics=M())
    res = run(sc.execute(StudentCreateLessonDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7,
        start_time=iso(4, 21), end_time="2030-06-05T00:00:00",
    )))
    assert res.lesson_id


def test_student_can_book_lesson_crossing_midnight():
    db = make_db()
    add_booking(db, 1, TUE, datetime.time(8, 0), datetime.time.max)
    add_booking(db, 2, WED, datetime.time(0, 0), datetime.time(18, 0))
    sc = StudentCreateLessonScenario(db=db, metrics=M())
    res = run(sc.execute(StudentCreateLessonDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7,
        start_time=iso(4, 21), end_time="2030-06-05T01:00:00",
    )))
    assert res.lesson_id


def test_booking_till_23_59_still_does_not_cover_midnight_minute():
    db = make_db()
    add_booking(db, 1, TUE, datetime.time(8, 0), datetime.time(23, 59))
    sc = StudentCreateLessonScenario(db=db, metrics=M())
    with pytest.raises(ValidationError):
        run(sc.execute(StudentCreateLessonDTO(
            access_token=create_access_token(11, "student"), tutor_user_id=7,
            start_time=iso(4, 21), end_time="2030-06-05T00:00:00",
        )))


# ---套餐 4: слоты самозаписи вычитают уроки, пересекающие полночь ---


def test_slots_hide_midnight_crossing_lesson_of_other_tutor():
    db = make_db()
    add_booking(db, 1, WED, datetime.time(0, 0), datetime.time(18, 0))
    # Урок ученика у ДРУГОГО репетитора: 04.06 23:30 -> 05.06 01:00.
    db.lessons[900] = {
        "id": 900, "tutor_id": 77, "is_group": False, "status": "SCHEDULED",
        "start_time": datetime.datetime(2030, 6, 4, 23, 30),
        "end_time": datetime.datetime(2030, 6, 5, 1, 0),
    }
    db.participants[600] = {"id": 600, "lesson_id": 900, "student_id": 5, "participant_settings": None}

    sc = StudentGetAvailableSlotsScenario(db=db, metrics=M())
    res = run(sc.execute(StudentGetAvailableSlotsDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7,
        date_from="2030-06-05", date_to="2030-06-05",
    )))
    day5 = [(s.start, s.end) for s in res.slots]
    assert ("2030-06-05T01:00:00", "2030-06-05T18:00:00") in day5
    assert not any(s == "2030-06-05T00:00:00" for s, _ in day5), \
        "Час, занятый у другого репетитора [00:00,01:00), не должен попадать в свободные слоты"


# ---套餐 6: busy-slots учителя учитывают ночные уроки ---


def test_busy_slots_include_lesson_crossing_into_range():
    db = make_db()
    db.lessons[900] = {
        "id": 900, "tutor_id": 42, "is_group": False, "status": "SCHEDULED",
        "start_time": datetime.datetime(2030, 6, 4, 23, 0),
        "end_time": datetime.datetime(2030, 6, 5, 1, 0),
    }
    db.participants[600] = {"id": 600, "lesson_id": 900, "student_id": 5, "participant_settings": None}

    sc = TutorGetStudentBusySlotsScenario(db=db, metrics=M())
    res = run(sc.execute(TutorGetStudentBusySlotsDTO(
        access_token=create_access_token(7, "tutor"), student_user_id=11,
        date_from="2030-06-05", date_to="2030-06-05",
    )))
    # По правилу пересечения интервалов урок попадает в занятость
    # на день, куда он "перетекает" (дата старта урока до диапазона).
    intervals = [(s.start, s.end) for s in res.busy_slots]
    assert intervals == [("2030-06-04T23:00:00", "2030-06-05T01:00:00")]


# ---套餐 8: конкурентное создание уроков сериализовано локом репетитора ---


def _slow_query(db, delay: float):
    orig = db.query

    async def query(sql, params, **kwargs):
        await asyncio.sleep(delay)
        return await orig(sql, params, **kwargs)

    db.query = query
    return db


def test_concurrent_creates_do_not_double_book():
    db = _slow_query(make_db(), delay=0.02)
    add_booking(db, 1, TUE, datetime.time(8, 0), datetime.time(18, 0))

    async def scenario():
        results = []

        async def create(user_id: int):
            sc = StudentCreateLessonScenario(db=db, metrics=M())
            dto = StudentCreateLessonDTO(
                access_token=create_access_token(user_id, "student"), tutor_user_id=7,
                start_time=iso(4, 10), end_time=iso(4, 11),
            )
            try:
                results.append(("created", (await sc.execute(dto)).lesson_id))
            except Exception as e:  # noqa: BLE001
                results.append(("failed", type(e).__name__))

        await asyncio.gather(create(11), create(99))
        return results

    results = asyncio.run(scenario())
    created = [r for r in results if r[0] == "created"]
    failed = [r for r in results if r[0] == "failed"]
    assert len(created) == 1, f"двойное бронирование: {results}"
    assert len(db.lessons) == 1, f"в БД два пересекающихся урока: {results}"
    assert failed, f"второй запрос должен получить отказ: {results}"
