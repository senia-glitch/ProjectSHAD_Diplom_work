# Тесты снапшота цены: ставка/скидка связи фиксируются в строке
# участия в момент добавления ученика в урок и дальше не плывут.
# Запуск: pytest tests/test_price_snapshot.py -q
import asyncio
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.utils.security import create_access_token
from app.utils.json_codec import parse_row
from app.utils.participants import build_price_snapshot, final_price_per_hour
from app.scenarios.tutor.participants import (
    TutorAddParticipantDTO,
    TutorAddParticipantScenario,
)
from app.scenarios.student.lessons import (
    StudentCreateLessonDTO,
    StudentCreateLessonScenario,
    StudentJoinLessonDTO,
    StudentJoinLessonScenario,
)


def dt(day, h, m=0):
    return datetime.datetime(2030, 6, day, h, m)


def iso(day, h, m=0):
    return dt(day, h, m).isoformat()


WEEKDAYS = {
    0: "MONDAY", 1: "TUESDAY", 2: "WEDNESDAY", 3: "THURSDAY",
    4: "FRIDAY", 5: "SATURDAY", 6: "SUNDAY",
}


# --- pure-хелперы ---


def test_final_price_mirrors_frontend():
    assert final_price_per_hour(1000, 40) == 600
    assert final_price_per_hour(1000, 0) == 1000
    assert final_price_per_hour(999, 10) == 899


def test_snapshot_shape():
    snap = build_price_snapshot(2000, 10, 77, now=datetime.datetime(2030, 1, 5, 9, 0))
    inner = snap["price_snapshot"]
    assert inner["hourly_rate"] == 2000
    assert inner["discount"] == 10
    assert inner["final_per_hour"] == 1800
    assert inner["currency"] == "RUB"
    assert inner["config_id"] == 77
    assert inner["snapshot_at"] == "2030-01-05T09:00:00"


# --- stub-БД ---


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.tutors = {}            # user_id -> tutor_id
        self.students = {}          # user_id -> student_id
        self.student_settings = {}  # student_id -> row
        self.tutor_settings = {}    # tutor_id -> row
        self.configs = []           # configurations rows
        self.bookings = []          # bookings rows
        self.lessons = {}           # id -> row
        self.participants = {}      # id -> row
        self._next_lesson = 100
        self._next_part = 500

    async def query(self, sql, params):
        if '"tutors"' in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        if '"students"' in sql:
            if "user_id" in sql:
                uid = params.get("uid")
                return [{"id": self.students[uid]}] if uid in self.students else []
            sid = params.get("sid")
            rows = [
                {"id": sid_, "user_id": uid}
                for uid, sid_ in self.students.items() if sid_ == sid
            ]
            return rows
        if '"student_settings"' in sql:
            sid = params.get("sid")
            return [self.student_settings[sid]] if sid in self.student_settings else []
        if '"tutor_settings"' in sql:
            tid = params.get("tid")
            return [self.tutor_settings[tid]] if tid in self.tutor_settings else []
        if '"configurations"' in sql:
            return [
                c for c in self.configs
                if c["student_id"] == params.get("sid") and c["tutor_id"] == params.get("tid")
            ]
        if '"bookings"' in sql:
            wd = params.get("wd")
            return [
                b for b in self.bookings
                if b["tutor_id"] == params.get("tid") and (wd is None or b["weekday"] == wd)
            ]
        if '"lesson_participants"' in sql:
            if "student_id" in sql and "lesson_id" in sql:
                return [
                    dict(p) for p in self.participants.values()
                    if p["lesson_id"] == params.get("lid") and p["student_id"] == params.get("sid")
                ]
            if "student_id" in sql:
                return [
                    dict(p) for p in self.participants.values()
                    if p["student_id"] == params.get("sid")
                ]
            if "lesson_id" in sql:
                return [
                    dict(p) for p in self.participants.values()
                    if p["lesson_id"] == params.get("lid")
                ]
            return [dict(p) for p in self.participants.values()]
        if '"lessons"' in sql:
            if "end_time > :ds" in sql:
                # Строгое пересечение с UTC-диапазоном (расчёт свободных окон).
                return [
                    dict(l) for l in self.lessons.values()
                    if ("tutor_id = :tid" not in sql or l["tutor_id"] == params.get("tid"))
                    and l["start_time"] < params.get("de") and l["end_time"] > params.get("ds")
                ]
            if "start_time >=" in sql:
                return [
                    dict(l) for l in self.lessons.values()
                    if l["tutor_id"] == params.get("tid")
                    and params.get("ds") <= l["start_time"] <= params.get("de")
                ]
            lid = params.get("lid")
            if lid is not None and lid in self.lessons:
                row = self.lessons[lid]
                if "tutor_id" in sql and row["tutor_id"] != params.get("tid"):
                    return []
                return [dict(row)]
            return []
        return []

    async def create(self, table, data):
        if table == "lessons":
            self._next_lesson += 1
            row = {"id": self._next_lesson, "status": "SCHEDULED", **data}
            self.lessons[row["id"]] = row
            return dict(row)
        if table == "lesson_participants":
            self._next_part += 1
            row = {"id": self._next_part, **data}
            self.participants[row["id"]] = row
            return dict(row)
        raise AssertionError(table)

    async def update(self, table, rid, data):
        self.lessons[rid].update(data)
        return dict(self.lessons[rid])

    async def read(self, table, rid):
        return dict(self.lessons[rid])

    async def delete(self, table, rid):
        del self.participants[rid]
        return True


def seed_pair(db, rate=2000, discount=10):
    db.tutors[7] = 42
    db.students[11] = 5
    db.student_settings[5] = {"student_id": 5, "status": "ACTIVE"}
    db.tutor_settings[42] = {
        "tutor_id": 42, "work_status": "WORKING",
        "self_booking_mode": "YES", "self_booking_whitelist": None,
    }
    db.configs.append({
        "id": 77, "student_id": 5, "tutor_id": 42,
        "hourly_rate": rate, "discount": discount,
        "allow_self_booking": True, "booking_lead_time_hours": 0,
        "default_links": None,
    })


def snapshot_of(db, lesson_id, student_id):
    rows = [
        p for p in db.participants.values()
        if p["lesson_id"] == lesson_id and p["student_id"] == student_id
    ]
    assert rows, "participant not created"
    parsed = parse_row("lesson_participants", rows[0])
    return (parsed.get("participant_settings") or {}).get("price_snapshot")


def run(coro):
    return asyncio.run(coro)


# --- сценарии ---


def test_tutor_add_writes_snapshot():
    db = StubDB()
    seed_pair(db)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": dt(10, 10), "end_time": dt(10, 11),
        "is_group": False, "status": "SCHEDULED",
    }
    sc = TutorAddParticipantScenario(db=db, metrics=DummyMetrics())
    dto = TutorAddParticipantDTO(
        access_token=create_access_token(7, "tutor"),
        lesson_id=1, student_user_id=11,
    )
    res = run(sc.execute(dto))
    snap = snapshot_of(db, 1, 5)
    assert res.participant_id
    assert snap["final_per_hour"] == 1800
    assert snap["hourly_rate"] == 2000
    assert snap["discount"] == 10
    assert snap["config_id"] == 77


def test_tutor_add_without_config_forbidden():
    from app.core.exceptions import ForbiddenError
    import pytest
    db = StubDB()
    seed_pair(db)
    db.configs.clear()
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": dt(10, 10), "end_time": dt(10, 11),
        "is_group": False, "status": "SCHEDULED",
    }
    sc = TutorAddParticipantScenario(db=db, metrics=DummyMetrics())
    dto = TutorAddParticipantDTO(
        access_token=create_access_token(7, "tutor"),
        lesson_id=1, student_user_id=11,
    )
    with pytest.raises(ForbiddenError):
        run(sc.execute(dto))


def test_student_join_writes_snapshot():
    db = StubDB()
    seed_pair(db, rate=1500, discount=20)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": dt(10, 10), "end_time": dt(10, 11),
        "is_group": True, "status": "SCHEDULED",
    }
    sc = StudentJoinLessonScenario(db=db, metrics=DummyMetrics())
    dto = StudentJoinLessonDTO(
        access_token=create_access_token(11, "student"), lesson_id=1
    )
    run(sc.execute(dto))
    snap = snapshot_of(db, 1, 5)
    assert snap["final_per_hour"] == 1200
    assert snap["config_id"] == 77


def test_student_create_writes_snapshot():
    db = StubDB()
    seed_pair(db, rate=1500, discount=20)
    day = dt(4, 10)
    db.bookings.append({
        "id": 1, "tutor_id": 42, "weekday": WEEKDAYS[day.weekday()],
        "start_time": datetime.time(8, 0), "end_time": datetime.time(18, 0),
        "access_rule": "EVERYONE", "access_targets": None,
    })
    sc = StudentCreateLessonScenario(db=db, metrics=DummyMetrics())
    dto = StudentCreateLessonDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7,
        start_time=iso(4, 10), end_time=iso(4, 11),
    )
    res = run(sc.execute(dto))
    snap = snapshot_of(db, res.lesson_id, 5)
    assert snap["final_per_hour"] == 1200
    assert snap["hourly_rate"] == 1500


def test_snapshot_survives_codec_roundtrip():
    snap = build_price_snapshot(2000, 10, 77)
    raw = json.dumps({"price_snapshot": snap["price_snapshot"]})
    parsed = parse_row("lesson_participants", {"participant_settings": raw})
    assert parsed["participant_settings"]["price_snapshot"]["final_per_hour"] == 1800
