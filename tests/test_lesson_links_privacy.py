# Тесты приватности lesson_links: чужие уроки репетитора отдаются
# без ссылок, свои — со ссылками.
# Запуск: pytest tests/test_lesson_links_privacy.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.utils.security import create_access_token
from app.scenarios.student.lessons import (
    StudentGetTutorLessonsDTO,
    StudentGetTutorLessonsScenario,
)

LINKS = [{"alias": "Zoom", "url": "https://example.com/zoom"}]


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.students = {11: 5}
        self.tutors = {7: 42}
        self.configs = [{"id": 77, "student_id": 5, "tutor_id": 42}]
        self.lessons = {}
        self.participants = {}

    async def query(self, sql, params, **kwargs):
        if '"students"' in sql:
            return [{"id": 5}] if params.get("uid") in self.students else []
        if '"tutors"' in sql:
            return [{"id": 42}] if params.get("uid") in self.tutors else []
        if '"configurations"' in sql:
            return [
                dict(c) for c in self.configs
                if c["student_id"] == params.get("sid") and c["tutor_id"] == params.get("tid")
            ]
        if '"lesson_participants"' in sql:
            sid = params.get("sid")
            return [dict(p) for p in self.participants.values() if p["student_id"] == sid]
        if '"lessons"' in sql:
            tid = params.get("tid")
            return [dict(l) for l in self.lessons.values() if l["tutor_id"] == tid]
        return []


def _lesson(lid, links):
    return {
        "id": lid, "tutor_id": 42,
        "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11),
        "is_group": True, "status": "SCHEDULED", "lesson_links": links,
    }


def test_links_hidden_for_lessons_without_participation():
    db = StubDB()
    db.lessons[1] = _lesson(1, LINKS)
    db.lessons[2] = _lesson(2, LINKS)
    db.participants[501] = {
        "id": 501, "lesson_id": 1, "student_id": 5, "participant_settings": None,
    }
    sc = StudentGetTutorLessonsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentGetTutorLessonsDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7)))
    by_id = {l.lesson_id: l for l in res.lessons}
    assert by_id[1].lesson_links == LINKS
    assert by_id[2].lesson_links is None


def test_links_hidden_for_cancelled_participation():
    db = StubDB()
    db.lessons[1] = _lesson(1, LINKS)
    db.participants[501] = {
        "id": 501, "lesson_id": 1, "student_id": 5,
        "participant_settings": '{"cancelled": {"by": "student", "at": "2030-06-01T09:00:00"}}',
    }
    sc = StudentGetTutorLessonsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentGetTutorLessonsDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7)))
    assert len(res.lessons) == 1
    assert res.lessons[0].lesson_links is None