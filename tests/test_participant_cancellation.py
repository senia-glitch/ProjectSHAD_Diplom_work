# Отмена записей уроков: пометка вместо удаления, возврат, скрытие, инициаторы.
# Правила:
# - leave/remove помечают participant_settings.cancelled={by,at}, строка остаётся;
# - join/add на отменённой записи гасят отмену (снапшот и paid не трогаем);
# - отменённые записи скрыты везде, кроме агрегированной статистики;
# - отменённые уроки (CANCELLED) не занимают слоты и не сторожат overlap;
# - оплата отменённой записи запрещена.
# Запуск: pytest tests/test_participant_cancellation.py -q
import asyncio
import datetime
from app.utils.clock import utc_now
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.utils.security import create_access_token
from app.scenarios.student.lessons import (
    StudentJoinLessonDTO, StudentJoinLessonScenario,
    StudentLeaveLessonDTO, StudentLeaveLessonScenario,
    StudentGetMyLessonsDTO, StudentGetMyLessonsScenario,
)
from app.scenarios.tutor.participants import (
    TutorAddParticipantDTO, TutorAddParticipantScenario,
    TutorRemoveParticipantDTO, TutorRemoveParticipantScenario,
    TutorSetPaymentDTO, TutorSetPaymentScenario,
)
from app.scenarios.tutor.lessons import (
    TutorCreateLessonDTO, TutorCreateLessonScenario,
    TutorUpdateLessonDTO, TutorUpdateLessonScenario,
)
from app.scenarios.tutor.statistics import (
    TutorGetStatisticsDTO, TutorGetStatisticsScenario,
)
from app.scenarios.tutor.lesson_details import (
    TutorLessonDetailsDTO, TutorLessonDetailsScenario,
)
from app.scenarios.tutor.students import (
    TutorGetStudentBusySlotsDTO, TutorGetStudentBusySlotsScenario,
)


def dt_future(days=3, h=10):
    d = utc_now() + datetime.timedelta(days=days)
    return d.replace(hour=h, minute=0, second=0, microsecond=0)


def iso(d):
    return d.isoformat()


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    """Честный стаб: хранит ровно то, что пришло в create/update
    (JSON-строки настроек), как настоящий драйвер."""

    def __init__(self):
        self.tutors = {7: 42}
        self.students = {11: 5}
        self.users = {11: "Иван", 12: "Пётр"}
        self.configs = [{
            "id": 77, "student_id": 5, "tutor_id": 42,
            "hourly_rate": 2000, "discount": 0,
            "allow_self_booking": True,
        }]
        self.tutor_settings = {42: {"tutor_id": 42, "work_status": "WORKING"}}
        self.statuses = {5: "ACTIVE"}
        self.lessons = {}
        self.participants = {}
        self._next_lesson = 100
        self._next_part = 500

    # -- seed --
    def seed_lesson(self, lid, start, end, status="SCHEDULED", is_group=False):
        self.lessons[lid] = {
            "id": lid, "tutor_id": 42, "created_by_id": 7,
            "start_time": start, "end_time": end, "status": status,
            "is_group": is_group,
        }

    def seed_participant(self, lid, sid, settings=None):
        self._next_part += 1
        import json as _json
        self.participants[self._next_part] = {
            "id": self._next_part, "lesson_id": lid, "student_id": sid,
            "participant_settings": _json.dumps(settings or {}, ensure_ascii=False),
        }
        return self._next_part

    # -- api --
    async def query(self, sql, params):
        if '"tutors"' in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        # Ветка только для прямых выборок из students: JOIN-запросы
        # со students (статистика/details) обслуживаются ниже по своим таблицам.
        if '"students"' in sql and '"lesson_participants"' not in sql and '"lessons"' not in sql:
            uid = params.get("uid")
            if uid is not None:
                return [{"id": self.students[uid]}] if uid in self.students else []
            sid = params.get("sid")
            return [{"id": s, "user_id": u} for u, s in self.students.items() if s == sid]
        if '"student_settings"' in sql:
            if '"configurations"' in sql:
                # Статусы учеников репетитора для статистики.
                linked = {c["student_id"] for c in self.configs if c["tutor_id"] == params.get("tid")}
                return [{"student_id": sid, "status": self.statuses.get(sid, "ACTIVE")} for sid in linked]
            sid = params.get("sid")
            if sid in self.statuses:
                return [{"student_id": sid, "status": self.statuses[sid]}]
            return []
        if '"tutor_settings"' in sql:
            tid = params.get("tid")
            return [self.tutor_settings[tid]] if tid in self.tutor_settings else []
        if '"configurations"' in sql:
            return [c for c in self.configs
                    if (params.get("sid") is None or c["student_id"] == params.get("sid"))
                    and c["tutor_id"] == params.get("tid")]
        if '"lesson_participants"' in sql:
            if "GROUP BY" in sql:
                return []
            # История: выбирает l.start_time БЕЗ lp.lesson_id.
            # Остальные запросы либо выбирают lp.lesson_id, либо точечные.
            head = sql.split("FROM")[0]
            if "l.start_time" in head and "lp.lesson_id" not in head:
                # История: student_id + start_time + settings.
                rows = []
                for p in self.participants.values():
                    lesson = self.lessons.get(p["lesson_id"])
                    if lesson is None or lesson["tutor_id"] != params.get("tid"):
                        continue
                    rows.append({
                        "student_id": p["student_id"],
                        "start_time": lesson["start_time"],
                        "participant_settings": p["participant_settings"],
                    })
                return rows
            # Точечные выборки по ключам.
            if params.get("lid") is not None or params.get("sid") is not None:
                rows = [dict(p) for p in self.participants.values()]
                if params.get("lid") is not None:
                    rows = [p for p in rows if p["lesson_id"] == params["lid"]]
                if params.get("sid") is not None:
                    rows = [p for p in rows if p["student_id"] == params["sid"]]
                return rows
            # Range-join (статистика/details/upcoming): эмулируем JOIN lessons.
            out = []
            for p in self.participants.values():
                lesson = self.lessons.get(p["lesson_id"])
                if lesson is None:
                    continue
                if params.get("tid") is not None and lesson["tutor_id"] != params["tid"]:
                    continue
                lo, hi = params.get("from"), params.get("to")
                if lo is not None and hi is not None:
                    if not (lo <= lesson["start_time"] < hi):
                        continue
                if "s1" in params and lesson.get("status") not in (params["s1"], params.get("s2")):
                    continue
                uid = next((u for u, s in self.students.items() if s == p["student_id"]), 0)
                out.append({
                    "lesson_id": p["lesson_id"], "student_id": p["student_id"],
                    "participant_settings": p["participant_settings"],
                    "start_time": lesson["start_time"], "end_time": lesson["end_time"],
                    "status": lesson.get("status"), "is_group": lesson.get("is_group", False),
                    "full_name": self.users.get(uid, f"Ученик #{p['student_id']}"),
                    "user_id": uid,
                })
            return out
        if '"lessons"' in sql:
            rows = [dict(l) for l in self.lessons.values()]
            if params.get("lid") is not None and "start_time <" not in sql:
                rows = [l for l in rows if l["id"] == params["lid"]]
                if "tutor_id" in sql:
                    rows = [l for l in rows if l["tutor_id"] == params.get("tid")]
                return rows
            if params.get("tid") is not None:
                rows = [l for l in rows if l["tutor_id"] == params["tid"]]
            if "start_time >=" in sql:
                lo = params.get("ds", params.get("from"))
                hi = params.get("to", params.get("de"))
                # statistics/details: [from, to); create/slots: [ds, de].
                if params.get("to") is not None or params.get("from") is not None:
                    rows = [l for l in rows if lo <= l["start_time"] < hi]
                else:
                    rows = [l for l in rows if lo <= l["start_time"] <= hi]
            if "start_time <" in sql and "end_time >" in sql:
                # Overlap-сторож.
                rows = [l for l in rows
                        if l["start_time"] < params["et"] and l["end_time"] > params["st"]]
                if params.get("lid") is not None:
                    rows = [l for l in rows if l["id"] != params["lid"]]
            if "CANCELLED" in sql:
                rows = [l for l in rows if (l.get("status") or "SCHEDULED") != "CANCELLED"]
            return rows
        return []

    async def create(self, table, data):
        if table == "lessons":
            self._next_lesson += 1
            row = {"id": self._next_lesson, "status": "SCHEDULED", **data}
            self.lessons[row["id"]] = row
            return dict(row)
        if table == "lesson_participants":
            for p in self.participants.values():
                if p["lesson_id"] == data["lesson_id"] and p["student_id"] == data["student_id"]:
                    raise Exception("uq_lesson_participant duplicate")
            self._next_part += 1
            row = {"id": self._next_part, **data}
            self.participants[row["id"]] = row
            return dict(row)
        raise AssertionError(table)

    async def update(self, table, rid, data):
        store = self.lessons if table == "lessons" else self.participants
        store[rid].update(data)
        return dict(store[rid])

    async def read(self, table, rid):
        store = self.lessons if table == "lessons" else self.participants
        return dict(store[rid])

    async def delete(self, table, rid):
        store = self.lessons if table == "lessons" else self.participants
        del store[rid]
        return True


def run(coro):
    return asyncio.run(coro)


def student_token():
    return create_access_token(11, "student")


def tutor_token():
    return create_access_token(7, "tutor")


def make_db():
    db = StubDB()
    return db


def test_cancellation_helpers():
    import json as _json
    from app.utils.participants import (
        cancellation_of, is_cancelled_row, build_cancellation, validate_not_cancelled,
    )
    from core import ValidationError
    import pytest
    assert cancellation_of(None) is None
    assert cancellation_of({}) is None
    assert cancellation_of({"cancelled": {"by": "student", "at": "x"}}) == {"by": "student", "at": "x"}
    assert cancellation_of({"cancelled": "oops"}) is None
    assert is_cancelled_row({"participant_settings": None}) is False
    assert is_cancelled_row({"participant_settings": _json.dumps({"cancelled": {"by": "tutor", "at": "x"}})}) is True
    assert is_cancelled_row({"participant_settings": {"paid": True}}) is False
    mark = build_cancellation("student")
    assert mark["by"] == "student" and mark["at"]
    with pytest.raises(ValidationError):
        validate_not_cancelled({"participant_settings": {"cancelled": {"by": "student", "at": "x"}}})


def test_leave_marks_and_is_idempotent():
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end)
    pid = db.seed_participant(1, 5)
    sc = StudentLeaveLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentLeaveLessonDTO(access_token=student_token(), lesson_id=1)))
    assert res.ok is True
    # Строка осталась, помечена учеником со временем.
    row = db.participants[pid]
    import json as _json
    cancelled = _json.loads(row["participant_settings"])["cancelled"]
    assert cancelled["by"] == "student"
    assert cancelled["at"]
    # Повторный выход — ok, не NotFound.
    res2 = run(sc.execute(StudentLeaveLessonDTO(access_token=student_token(), lesson_id=1)))
    assert res2.ok is True


def test_join_revives_and_keeps_snapshot():
    import json as _json
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end)
    pid = db.seed_participant(1, 5, {
        "price_snapshot": {"final_per_hour": 1500}, "paid": True,
        "cancelled": {"by": "student", "at": "2030-01-01T00:00:00"},
    })
    sc = StudentJoinLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentJoinLessonDTO(access_token=student_token(), lesson_id=1)))
    assert res.participant_id == pid
    settings = _json.loads(db.participants[pid]["participant_settings"])
    assert "cancelled" not in settings
    # Снапшот и paid не тронуты.
    assert settings["price_snapshot"] == {"final_per_hour": 1500}
    assert settings["paid"] is True


def test_tutor_remove_marks_and_add_revives():
    import json as _json
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end)
    pid = db.seed_participant(1, 5)
    rm = TutorRemoveParticipantScenario(db=db, metrics=DummyMetrics())
    assert run(rm.execute(TutorRemoveParticipantDTO(
        access_token=tutor_token(), lesson_id=1, student_user_id=11))).ok is True
    assert _json.loads(db.participants[pid]["participant_settings"])["cancelled"]["by"] == "tutor"
    add = TutorAddParticipantScenario(db=db, metrics=DummyMetrics())
    res = run(add.execute(TutorAddParticipantDTO(
        access_token=tutor_token(), lesson_id=1, student_user_id=11)))
    assert res.participant_id == pid
    assert "cancelled" not in _json.loads(db.participants[pid]["participant_settings"])


def test_tutor_cancel_marks_all_keep_first():
    import json as _json
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end)
    db.seed_participant(1, 5, {"cancelled": {"by": "student", "at": "2030-01-01T00:00:00"}})
    # Второй ученик.
    db.students[12] = 6
    db.seed_participant(1, 6, {})
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(TutorUpdateLessonDTO(
        access_token=tutor_token(), lesson_id=1, status="CANCELLED")))
    assert res.status == "CANCELLED"
    # Первая отмена (student) не перезаписана, активная помечена tutor.
    by = {p["student_id"]: _json.loads(p["participant_settings"]).get("cancelled", {}).get("by")
          for p in db.participants.values() if p["lesson_id"] == 1}
    assert by[5] == "student"
    assert by[6] == "tutor"


def test_my_lessons_keep_cancelled_in_history():
    """История отмен: отменённая запись остаётся у ученика со статусом и пометкой, кто отменил."""
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end, is_group=True)
    db.seed_lesson(2, dt_future(4, 10), dt_future(4, 11))
    db.seed_participant(1, 5, {"cancelled": {"by": "student", "at": "x", "reason": "болею"}})
    db.seed_participant(2, 5, {})
    sc = StudentGetMyLessonsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentGetMyLessonsDTO(access_token=student_token())))
    by_id = {l.lesson_id: l for l in res.lessons}
    assert sorted(by_id) == [1, 2]
    assert by_id[1].status == "CANCELLED"
    assert by_id[1].status_note["by"] == "student"
    assert by_id[1].status_note["reason"] == "болею"
    assert by_id[2].status == "SCHEDULED" and by_id[2].status_note is None


def test_overlap_ignores_cancelled_lesson():
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end, status="CANCELLED")
    sc = TutorCreateLessonScenario(db=db, metrics=DummyMetrics())
    # Поверх отменённого — создаётся без Conflict.
    res = run(sc.execute(TutorCreateLessonDTO(
        access_token=tutor_token(),
        start_time=iso(start), end_time=iso(end))))
    assert res.lesson_id != 1


def test_payment_forbidden_on_cancelled():
    import pytest
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end)
    db.seed_participant(1, 5, {"cancelled": {"by": "student", "at": "x"}})
    sc = TutorSetPaymentScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(Exception):
        run(sc.execute(TutorSetPaymentDTO(
            access_token=tutor_token(), lesson_id=1, student_user_id=11, paid=True)))


def test_statistics_initiators_and_revenue_exclusion():
    db = make_db()
    base = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    year = base.year
    start = base.replace(hour=10) + datetime.timedelta(days=2)
    end = start + datetime.timedelta(hours=1)
    if start.year != year:
        start = datetime.datetime(year, 6, 1, 10)
        end = datetime.datetime(year, 6, 1, 11)
    db.seed_lesson(1, start, end, status="FINISHED")
    db.seed_participant(1, 5, {
        "price_snapshot": {"final_per_hour": 2000}, "paid": True,
        "cancelled": {"by": "student", "at": "x"},
    })
    sc = TutorGetStatisticsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(TutorGetStatisticsDTO(access_token=tutor_token(), year=year)))
    # Отменённая оплаченная запись в выручку не идёт, но считается инициатором.
    assert res.totals.revenue == 0
    assert res.totals.lessons == 0
    assert res.totals.cancelled_by_student == 1
    assert res.totals.cancelled_by_tutor == 0


def test_details_hides_cancelled_with_counts():
    db = make_db()
    base = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = base.replace(hour=10) + datetime.timedelta(days=2)
    end = start + datetime.timedelta(hours=1)
    db.seed_lesson(1, start, end, status="FINISHED")
    db.seed_participant(1, 5, {
        "price_snapshot": {"final_per_hour": 2000},
        "cancelled": {"by": "tutor", "at": "x"},
    })
    sc = TutorLessonDetailsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(TutorLessonDetailsDTO(
        access_token=tutor_token(),
        date_from=start.date().isoformat(), date_to=end.date().isoformat())))
    assert res.lessons[0].students == []
    assert res.lessons[0].total == 0
    assert res.cancelled_by_tutor == 1
    assert res.cancelled_by_student == 0


def test_join_ongoing_allowed():
    db = make_db()
    now = utc_now()
    db.seed_lesson(1, now - datetime.timedelta(minutes=30), now + datetime.timedelta(minutes=30), is_group=True)
    sc = StudentJoinLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentJoinLessonDTO(access_token=student_token(), lesson_id=1)))
    assert res.participant_id
    assert db.lessons[1]["status"] == "ONGOING"


def test_leave_finished_forbidden():
    from core import ValidationError
    import pytest
    db = make_db()
    now = utc_now()
    db.seed_lesson(1, now - datetime.timedelta(hours=2), now - datetime.timedelta(hours=1), status="FINISHED")
    db.seed_participant(1, 5, {})
    sc = StudentLeaveLessonScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(StudentLeaveLessonDTO(access_token=student_token(), lesson_id=1)))
    # Строка на месте, выручка не тронута.
    assert len(db.participants) == 1


def test_tutor_remove_finished_forbidden():
    from core import ValidationError
    import pytest
    db = make_db()
    now = utc_now()
    db.seed_lesson(1, now - datetime.timedelta(hours=2), now - datetime.timedelta(hours=1), status="FINISHED")
    db.seed_participant(1, 5, {})
    sc = TutorRemoveParticipantScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorRemoveParticipantDTO(
            access_token=tutor_token(), lesson_id=1, student_user_id=11)))


def test_tutor_add_to_cancelled_forbidden():
    from core import ValidationError
    import pytest
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end, status="CANCELLED")
    sc = TutorAddParticipantScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorAddParticipantDTO(
            access_token=tutor_token(), lesson_id=1, student_user_id=11)))


def test_busy_slots_skip_cancelled():
    db = make_db()
    start, end = dt_future(3, 10), dt_future(3, 11)
    db.seed_lesson(1, start, end)
    db.seed_participant(1, 5, {"cancelled": {"by": "student", "at": "x"}})
    sc = TutorGetStudentBusySlotsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(TutorGetStudentBusySlotsDTO(
        access_token=tutor_token(), student_user_id=11,
        date_from=start.date().isoformat(), date_to=end.date().isoformat())))
    assert res.busy_slots == []
