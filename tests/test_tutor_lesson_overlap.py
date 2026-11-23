# Тесты сторожа пересечений уроков репетитора.
# Правило: новый урок не пересекается с существующими уроками того же
# репетитора; при переносе урок сам себя пересечением не считает.
# Интервал полуоткрытый [start, end): стык конец-в-конец разрешён.
# Запуск: pytest tests/test_tutor_lesson_overlap.py -q
import asyncio
import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ConflictError, ValidationError
from core.utils.security import create_access_token
from app.utils.lessons import check_lesson_overlap, resolve_effective_interval
from app.scenarios.tutor.lessons import (
    TutorCreateLessonDTO,
    TutorCreateLessonScenario,
    TutorUpdateLessonDTO,
    TutorUpdateLessonScenario,
)


def dt(day, h, m=0):
    return datetime.datetime(2030, 6, day, h, m)


def iso(day, h, m=0):
    return dt(day, h, m).isoformat()


# --- pure-хелперы ---


def test_check_overlap_empty_ok():
    assert check_lesson_overlap([]) is None


def test_check_overlap_raises():
    with pytest.raises(ConflictError):
        check_lesson_overlap([{"id": 1}])


def test_effective_interval_both_bounds():
    s, e, changed = resolve_effective_interval(dt(2, 10), dt(2, 11), dt(2, 12), dt(2, 13))
    assert (s, e, changed) == (dt(2, 12), dt(2, 13), True)


def test_effective_interval_single_bound():
    s, e, changed = resolve_effective_interval(dt(2, 10), dt(2, 11), dt(2, 9), None)
    assert (s, e, changed) == (dt(2, 9), dt(2, 11), True)


def test_effective_interval_unchanged():
    s, e, changed = resolve_effective_interval(dt(2, 10), dt(2, 11))
    assert (s, e, changed) == (dt(2, 10), dt(2, 11), False)


# --- stub-БД: честно исполняет SQL-зонды сценариев ---


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    """Минимальная БД для сценариев уроков. Зонд пересечений исполняет
    той же формулой, что SQL: start < :et AND end > :st (полуоткрытый)."""

    def __init__(self):
        self.tutors = {7: 42}
        self.lessons = {}
        self._next = 100

    def seed_lesson(self, lid, tutor_id, start, end):
        self.lessons[lid] = {
            "id": lid,
            "tutor_id": tutor_id,
            "start_time": start,
            "end_time": end,
            "is_group": False,
            "status": "SCHEDULED",
        }

    async def query(self, sql, params):
        if '"tutors"' in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        if '"tutor_settings"' in sql:
            return []
        if '"lessons"' in sql:
            if "start_time <" in sql:
                # Зонд пересечений.
                st, et = params["st"], params["et"]
                rows = [
                    dict(l) for l in self.lessons.values()
                    if l["tutor_id"] == params["tid"]
                    and l["start_time"] < et and l["end_time"] > st
                ]
                if "id != " in sql:
                    rows = [r for r in rows if r["id"] != params["lid"]]
                return rows
            lid = params.get("lid")
            if lid is not None and lid in self.lessons:
                row = self.lessons[lid]
                if "tutor_id" in sql and row["tutor_id"] != params.get("tid"):
                    return []
                return [dict(row)]
            return []
        return []

    async def create(self, table, data):
        assert table == "lessons"
        self._next += 1
        row = {"id": self._next, "status": "SCHEDULED", **data}
        self.lessons[row["id"]] = row
        return dict(row)

    async def update(self, table, rid, data):
        assert table == "lessons"
        self.lessons[rid].update(data)
        return dict(self.lessons[rid])

    async def read(self, table, rid):
        return dict(self.lessons[rid])

    async def delete(self, table, rid):
        del self.lessons[rid]
        return True


def make_db():
    db = StubDB()
    db.seed_lesson(1, 42, dt(2, 10), dt(2, 11))
    db.seed_lesson(2, 42, dt(2, 12), dt(2, 13))
    return db


def token():
    return create_access_token(7, "tutor")


def run(coro):
    return asyncio.run(coro)


# --- создание: пересечение запрещено, стык разрешён ---


def test_create_rejects_overlap():
    db = make_db()
    sc = TutorCreateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorCreateLessonDTO(
        access_token=token(), start_time=iso(2, 10, 30), end_time=iso(2, 11, 30)
    )
    with pytest.raises(ConflictError):
        run(sc.execute(dto))


def test_create_allows_adjacent():
    db = make_db()
    sc = TutorCreateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorCreateLessonDTO(
        access_token=token(), start_time=iso(2, 11), end_time=iso(2, 12)
    )
    res = run(sc.execute(dto))
    assert res.start_time == str(dt(2, 11))


def test_create_allows_disjoint():
    db = make_db()
    sc = TutorCreateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorCreateLessonDTO(
        access_token=token(), start_time=iso(2, 14), end_time=iso(2, 15)
    )
    res = run(sc.execute(dto))
    assert res.tutor_id == 42


def test_create_does_not_see_other_tutor():
    db = make_db()
    db.tutors[9] = 43
    sc = TutorCreateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorCreateLessonDTO(
        access_token=create_access_token(9, "tutor"),
        start_time=iso(2, 10, 30),
        end_time=iso(2, 11, 30),
    )
    res = run(sc.execute(dto))
    assert res.tutor_id == 43


# --- правка: чужое пересечение запрещено, себя не считаем ---


def test_update_rejects_overlap_with_other():
    db = make_db()
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorUpdateLessonDTO(
        access_token=token(), lesson_id=2,
        start_time=iso(2, 10, 30), end_time=iso(2, 11, 30),
    )
    with pytest.raises(ConflictError):
        run(sc.execute(dto))


def test_update_single_bound_overlap_rejected():
    db = make_db()
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorUpdateLessonDTO(
        access_token=token(), lesson_id=2, start_time=iso(2, 10, 30),
    )
    with pytest.raises(ConflictError):
        run(sc.execute(dto))


def test_update_own_time_kept_ok():
    db = make_db()
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorUpdateLessonDTO(
        access_token=token(), lesson_id=2,
        start_time=iso(2, 12), end_time=iso(2, 13),
    )
    res = run(sc.execute(dto))
    assert res.lesson_id == 2


def test_update_without_time_ok():
    db = make_db()
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorUpdateLessonDTO(access_token=token(), lesson_id=2, is_group=True)
    res = run(sc.execute(dto))
    assert res.lesson_id == 2
    assert db.lessons[2]["is_group"] is True


def test_update_inverted_interval_rejected():
    db = make_db()
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    dto = TutorUpdateLessonDTO(
        access_token=token(), lesson_id=2, start_time=iso(2, 14),
    )
    with pytest.raises(ValidationError):
        run(sc.execute(dto))
