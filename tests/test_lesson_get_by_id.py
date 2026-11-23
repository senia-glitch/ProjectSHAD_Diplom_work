# Тесты получения одного урока по id: страница урока.
# Репетитор — свой урок с участниками, суммами, отменёнными записями;
# студент — только свои незавершённые участия.
# Запуск: pytest tests/test_lesson_get_by_id.py -q
import asyncio
import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import NotFoundError
from core.utils.security import create_access_token
from app.scenarios.tutor.lessons import TutorGetLessonDTO, TutorGetLessonScenario
from app.scenarios.student.lessons import StudentGetLessonDTO, StudentGetLessonScenario


def run(coro):
    return asyncio.run(coro)


def dt(y, m, d, h, mi=0):
    return datetime.datetime(y, m, d, h, mi)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    """Тот же контур, что у детализации: tutors/students/users + lessons."""

    def __init__(self):
        self.tutors = {7: 42}
        self.students = {11: 5}
        self.users = {11: "Иван"}
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
            ]
        if '"lesson_participants"' in sql:
            if "u.full_name" in sql:
                return [{
                    "lesson_id": p["lesson_id"],
                    "student_id": p["student_id"],
                    "participant_settings": p["participant_settings"],
                    "full_name": self.users[11],
                    "user_id": 11,
                } for p in self.participants]
            return [dict(p) for p in self.participants if p["student_id"] == params["sid"]]
        if '"tutors"' in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        if '"students"' in sql:
            uid = params.get("uid")
            return [{"id": self.students[uid]}] if uid in self.students else []
        if '"configurations"' in sql:
            return [c for c in self.configs if c["tutor_id"] == params["tid"]]
        return []


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
        lesson_metadata={"room": "A-1"},
    )
    db.participants.append({
        "id": 0, "lesson_id": 1, "student_id": 5,
        "participant_settings": {"price_snapshot": snap(1800), "paid": True},
    })
    return db


def tutor_dto(**kw):
    base = dict(access_token=create_access_token(7, "tutor"), lesson_id=1)
    base.update(kw)
    return TutorGetLessonDTO(**base)


def student_dto(**kw):
    base = dict(access_token=create_access_token(11, "student"), lesson_id=1)
    base.update(kw)
    return StudentGetLessonDTO(**base)


# === Репетитор ===

def test_tutor_get_lesson_with_participants():
    res = run(TutorGetLessonScenario(db=make_db(), metrics=DummyMetrics())
              .execute(tutor_dto()))
    assert res.lesson_id == 1
    assert res.status == "FINISHED"
    assert res.descriptions == "Разбор дробей"
    assert res.links == [{"alias": "Материалы", "url": "https://example.com/1"}]
    assert res.metadata == {"room": "A-1"}
    assert len(res.students) == 1
    s = res.students[0]
    assert s.student_id == 5 and s.student_user_id == 11
    assert s.student_name == "Иван"
    assert s.amount == 1800 and s.estimated is False
    assert s.paid is True and s.cancelled is False
    assert res.total == 1800


def test_tutor_get_lesson_live_price_fallback():
    db = make_db()
    db.participants[0]["participant_settings"] = {"paid": False}
    res = run(TutorGetLessonScenario(db=db, metrics=DummyMetrics())
              .execute(tutor_dto()))
    # 2000 - 10% = 1800, пометка estimated: снапшота нет.
    assert res.students[0].amount == 1800
    assert res.students[0].estimated is True
    assert res.students[0].paid is False


def test_tutor_get_lesson_marks_cancelled_participant():
    db = make_db()
    db.participants[0]["participant_settings"] = {
        "price_snapshot": snap(1800),
        "paid": True,
        "cancelled": {"by": "student", "at": "2030-01-05T09:00:00"},
    }
    res = run(TutorGetLessonScenario(db=db, metrics=DummyMetrics())
              .execute(tutor_dto()))
    s = res.students[0]
    assert s.cancelled is True and s.cancelled_by == "student"
    # Отменённая запись не идёт в сумму.
    assert res.total == 0


def test_tutor_get_lesson_foreign_lesson_forbidden():
    db = make_db()
    db.seed_lesson(2, dt(2030, 3, 4, 10), dt(2030, 3, 4, 11), "SCHEDULED")
    # Урок 2 принадлежит tutor_id 42, но тутор смотрит чужой профиль.
    db.tutors = {7: 43}
    with pytest.raises(NotFoundError):
        run(TutorGetLessonScenario(db=db, metrics=DummyMetrics())
            .execute(tutor_dto(lesson_id=2)))


def test_tutor_get_lesson_unknown_id():
    with pytest.raises(NotFoundError):
        run(TutorGetLessonScenario(db=make_db(), metrics=DummyMetrics())
            .execute(tutor_dto(lesson_id=999)))


def test_tutor_get_lesson_without_tutor_profile():
    db = make_db()
    db.tutors = {}
    with pytest.raises(NotFoundError):
        run(TutorGetLessonScenario(db=db, metrics=DummyMetrics()).execute(tutor_dto()))


# === Студент ===

def test_student_get_lesson_own():
    res = run(StudentGetLessonScenario(db=make_db(), metrics=DummyMetrics())
              .execute(student_dto()))
    assert res.lesson_id == 1
    assert res.is_group is False
    assert res.start_time.startswith("2030-03-02 10:00")
    assert res.lesson_links == [{"alias": "Материалы", "url": "https://example.com/1"}]


def test_student_get_lesson_not_participant():
    db = make_db()
    db.participants[0]["lesson_id"] = 2
    db.seed_lesson(2, dt(2030, 3, 3, 10), dt(2030, 3, 3, 11), "SCHEDULED")
    with pytest.raises(NotFoundError):
        run(StudentGetLessonScenario(db=db, metrics=DummyMetrics()).execute(student_dto()))


def test_student_get_lesson_cancelled_participation_hidden():
    db = make_db()
    db.participants[0]["participant_settings"] = {
        "cancelled": {"by": "student", "at": "2030-01-05T09:00:00"},
    }
    with pytest.raises(NotFoundError):
        run(StudentGetLessonScenario(db=db, metrics=DummyMetrics()).execute(student_dto()))


def test_student_get_lesson_without_student_profile():
    db = make_db()
    db.students = {}
    with pytest.raises(NotFoundError):
        run(StudentGetLessonScenario(db=db, metrics=DummyMetrics()).execute(student_dto()))
