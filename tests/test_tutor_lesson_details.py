# Тесты детализации уроков для хронологии: строки с участниками,
# суммами, статусами, ссылками; фильтр по ученику; валидация диапазона.
# Запуск: pytest tests/test_tutor_lesson_details.py -q
import asyncio
import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ValidationError
from core.utils.security import create_access_token
from app.scenarios.tutor.lesson_details import (
    TutorLessonDetailsDTO,
    TutorLessonDetailsScenario,
)
from app.scenarios.tutor.participants import (
    TutorSetPaymentDTO,
    TutorSetPaymentScenario,
)


def dt(y, m, d, h, mi=0):
    return datetime.datetime(y, m, d, h, mi)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.tutors = {7: 42}
        self.users = {11: "Иван"}
        self.students = {11: 5}
        self.configs = [{
            "id": 77, "student_id": 5, "tutor_id": 42,
            "hourly_rate": 2000, "discount": 10,
        }]
        self.lessons = {}
        self.participants = []

    def seed_lesson(self, lid, start, end, status="SCHEDULED", **extra):
        self.lessons[lid] = {
            "id": lid, "tutor_id": 42,
            "start_time": start, "end_time": end, "status": status,
            "is_group": False, "lesson_descriptions": None, "lesson_links": None,
            **extra,
        }

    async def query(self, sql, params):
        if '"lessons"' in sql and '"lesson_participants"' not in sql:
            return [
                dict(l) for l in self.lessons.values()
                if ("tid" not in params or l["tutor_id"] == params["tid"])
                and ("lid" not in params or l["id"] == params["lid"])
                and ("from" not in params or params["from"] <= l["start_time"] < params["to"])
            ]
        if '"lesson_participants"' in sql:
            rows = []
            for p in self.participants:
                lesson = self.lessons[p["lesson_id"]]
                if "tid" in params and lesson["tutor_id"] != params["tid"]:
                    continue
                if "from" in params and not (params["from"] <= lesson["start_time"] < params["to"]):
                    continue
                if "s1" in params and lesson["status"] not in (params["s1"], params["s2"]):
                    continue
                if "lid" in params and p["lesson_id"] != params["lid"]:
                    continue
                if "sid" in params and p["student_id"] != params["sid"]:
                    continue
                uid = next(u for u, s in self.students.items() if s == p["student_id"])
                rows.append({
                    "id": p["id"], "lesson_id": p["lesson_id"], "student_id": p["student_id"],
                    "participant_settings": p["participant_settings"],
                    "full_name": self.users[uid], "user_id": uid,
                })
            return rows
        if '"tutors"' in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        if '"students"' in sql:
            uid = params.get("uid")
            return [{"id": self.students[uid]}] if uid in self.students else []
        if '"configurations"' in sql:
            return [c for c in self.configs if c["tutor_id"] == params["tid"]]
        return []

    async def update(self, table, rid, data):
        assert table == "lesson_participants"
        row = next(p for p in self.participants if p["id"] == rid)
        row.update(data)
        return dict(row)


def snap(price):
    return {
        "hourly_rate": 2000, "discount": 10, "final_per_hour": price,
        "currency": "RUB", "config_id": 77, "snapshot_at": "2030-01-05T09:00:00",
    }


def make_db():
    db = StubDB()
    db.seed_lesson(
        1, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED",
        lesson_descriptions="Разбор дробей",
        lesson_links=[{"alias": "Материалы", "url": "https://example.com/1"}],
    )
    db.participants.append({
        "id": 0, "lesson_id": 1, "student_id": 5,
        "participant_settings": {"price_snapshot": snap(1800)},
    })
    db.seed_lesson(2, dt(2030, 3, 3, 10), dt(2030, 3, 3, 11), "CANCELLED")
    db.participants.append({"id": 1, "lesson_id": 2, "student_id": 5, "participant_settings": None})
    return db


def run(coro):
    return asyncio.run(coro)


def dto(**kw):
    base = dict(access_token=create_access_token(7, "tutor"),
                date_from="2030-03-01", date_to="2030-03-31")
    base.update(kw)
    return TutorLessonDetailsDTO(**base)


def test_rows_with_amounts_links_notes():
    db = make_db()
    sc = TutorLessonDetailsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(dto()))
    assert len(res.lessons) == 2
    first = res.lessons[0]
    assert (first.date, first.start, first.end, first.minutes) == ("2030-03-02", "10:00", "11:00", 60)
    assert first.status == "FINISHED"
    assert first.descriptions == "Разбор дробей"
    assert first.links == [{"alias": "Материалы", "url": "https://example.com/1"}]
    assert first.total == 1800
    assert first.students[0].student_name == "Иван"
    assert first.students[0].estimated is False
    assert first.students[0].student_user_id == 11
    assert res.lessons[1].status == "CANCELLED"


def test_student_filter_drops_empty_lessons():
    db = make_db()
    sc = TutorLessonDetailsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(dto(student_ids="999")))
    assert res.lessons == []


def test_range_validation():
    db = make_db()
    sc = TutorLessonDetailsScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(dto(date_from="2030-03-10", date_to="2030-03-01")))
    with pytest.raises(ValidationError):
        run(sc.execute(dto(date_from="2028-01-01", date_to="2030-01-01")))


def pay_dto(**kw):
    base = dict(access_token=create_access_token(7, "tutor"),
                lesson_id=1, student_user_id=11, paid=True)
    base.update(kw)
    return TutorSetPaymentDTO(**base)


def details_paid(db):
    sc = TutorLessonDetailsScenario(db=db, metrics=DummyMetrics())
    return run(sc.execute(dto())).lessons[0].students[0].paid


def test_payment_default_false():
    assert details_paid(make_db()) is False


def test_payment_set_and_unset():
    db = make_db()
    sc = TutorSetPaymentScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(pay_dto(paid=True)))
    assert (res.lesson_id, res.student_id, res.paid) == (1, 5, True)
    assert details_paid(db) is True
    # Снапшот цены не затёрт флагом (в БД лежит JSON-строкой — как в проде).
    import json as _json
    stored = db.participants[0]["participant_settings"]
    stored = _json.loads(stored) if isinstance(stored, str) else stored
    assert stored["price_snapshot"]["final_per_hour"] == 1800
    assert stored["paid"] is True
    res = run(sc.execute(pay_dto(paid=False)))
    assert res.paid is False
    assert details_paid(db) is False


def test_payment_unknown_participant():
    from core import NotFoundError
    db = make_db()
    sc = TutorSetPaymentScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(NotFoundError):
        run(sc.execute(pay_dto(student_user_id=999)))
