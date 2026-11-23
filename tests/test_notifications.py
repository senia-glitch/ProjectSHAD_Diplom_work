# Тесты системы уведомлений: хелперы, сценарии списка/прочтения,
# эмиссия событий в сценариях уроков.
# Запуск: pytest tests/test_notifications.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core import NotFoundError
from core.utils.security import create_access_token
from core.dto import BaseDTO
from app.utils.notifications import notify_user, notify_participants, format_lesson_time
from app.scenarios.notifications.my import (
    NotificationsListScenario,
    NotificationsUnreadCountScenario,
    NotificationsMarkReadDTO,
    NotificationsMarkReadScenario,
    NotificationsReadAllScenario,
)
from tests.test_price_snapshot import StubDB as SnapshotStub, seed_pair, dt, iso, WEEKDAYS
from app.scenarios.student.lessons import (
    StudentCreateLessonDTO,
    StudentCreateLessonScenario,
)
from app.scenarios.tutor.participants import (
    TutorSetPaymentDTO,
    TutorSetPaymentScenario,
)


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.notifications = {}
        self.users = {}
        self.participants = []
        self.student_rows = {}
        self.created = []
        self._next = 0

    async def query(self, sql, params, **kwargs):
        if '"users"' in sql:
            uid = params.get("uid")
            if uid in self.users:
                return [dict(self.users[uid])]
            return []
        if '"students"' in sql:
            sid = params.get("sid")
            row = self.student_rows.get(sid)
            return [{"user_id": row}] if row is not None else []
        if '"lesson_participants"' in sql:
            lid = params.get("lid")
            return [dict(p) for p in self.participants if p["lesson_id"] == lid]
        if '"notifications"' in sql and "COUNT" in sql:
            unread = sum(
                1 for n in self.notifications.values()
                if n["user_id"] == params.get("uid") and n.get("read_at") is None
            )
            return [{"cnt": unread}]
        if '"notifications"' in sql:
            nid = params.get("nid")
            uid = params.get("uid")
            rows = [dict(n) for n in self.notifications.values() if uid is None or n["user_id"] == uid]
            if "read_at IS NULL" in sql:
                rows = [r for r in rows if r.get("read_at") is None]
            if nid is not None:
                rows = [r for r in rows if r["id"] == nid]
            rows.sort(key=lambda r: -r["id"])
            off = params.get("off") or 0
            lim = params.get("lim")
            rows = rows[off:] if lim is None else rows[off:off + lim]
            return rows
        return []

    async def create(self, table, data, **kwargs):
        if table == "notifications":
            self._next += 1
            row = {
                "id": self._next,
                "created_at": datetime.datetime(2030, 1, 1, 10, 0),
                "read_at": None,
                **data,
            }
            self.notifications[row["id"]] = row
            self.created.append(row)
            return dict(row)
        raise AssertionError(table)

    async def update(self, table, rid, data, **kwargs):
        if table == "notifications":
            self.notifications[rid].update(data)
            return dict(self.notifications[rid])
        raise AssertionError(table)

    async def read(self, table, rid, **kwargs):
        raise AssertionError(table)

    async def delete(self, table, rid, **kwargs):
        raise AssertionError(table)


class CaptureStub(SnapshotStub):
    def __init__(self):
        super().__init__()
        self.notifications_created = []

    async def query(self, sql, params):
        if '"tutors"' in sql:
            tid = params.get("tid")
            uid = params.get("uid")
            if tid is not None and tid == 42:
                return [{"user_id": 7}]
            if uid is not None and uid in self.tutors:
                return [{"id": self.tutors[uid]}]
            return []
        if '"users"' in sql:
            return []
        return await super().query(sql, params)

    async def create(self, table, data):
        if table == "notifications":
            self.notifications_created.append(data)
            return {"id": 900, **data}
        return await super().create(table, data)

    async def update(self, table, rid, data):
        if table == "lesson_participants":
            self.participants[rid].update(data)
            return dict(self.participants[rid])
        return await super().update(table, rid, data)


def test_format_lesson_time():
    assert format_lesson_time(datetime.datetime(2030, 6, 1, 10, 0)) == "01.06.2030 10:00"
    assert format_lesson_time("2030-06-01T10:00:00") == "01.06.2030 10:00"


def test_notify_user_creates_row():
    db = StubDB()
    run(notify_user(db, 11, "lesson_booked", "Ученик Иван записался на урок 01.06.2030 10:00"))
    assert len(db.created) == 1
    row = db.created[0]
    assert row["user_id"] == 11
    assert row["type"] == "lesson_booked"
    assert "Иван" in row["payload"]


def test_notify_user_swallows_failures():
    class BrokenDB(StubDB):
        async def create(self, table, data, **kwargs):
            raise RuntimeError("db down")

    run(notify_user(BrokenDB(), 11, "t", "text"))


def test_notify_participants_skips_cancelled():
    db = StubDB()
    db.student_rows = {5: 11, 6: 12}
    db.participants = [
        {"lesson_id": 1, "student_id": 5, "participant_settings": None},
        {"lesson_id": 1, "student_id": 6,
         "participant_settings": '{"cancelled": {"by": "student", "at": "2030-01-01T10:00:00"}}'},
    ]
    run(notify_participants(db, 1, "lesson_status_changed", "Урок отменён"))
    assert len(db.created) == 1
    assert db.created[0]["user_id"] == 11


def test_notifications_list_and_unread():
    db = StubDB()
    db.notifications[1] = {
        "id": 1, "user_id": 11, "type": "t", "payload": '{"text": "А"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 1),
    }
    db.notifications[2] = {
        "id": 2, "user_id": 11, "type": "t", "payload": '{"text": "Б"}',
        "read_at": datetime.datetime(2030, 1, 2), "created_at": datetime.datetime(2030, 1, 2),
    }
    sc = NotificationsListScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(BaseDTO(access_token=create_access_token(11, "student"))))
    assert res.unread_count == 1
    assert [n.id for n in res.notifications] == [2, 1]
    assert res.notifications[0].read is True
    assert res.notifications[1].read is False
    assert res.notifications[1].text == "А"


def test_unread_count_scenario():
    db = StubDB()
    db.notifications[1] = {
        "id": 1, "user_id": 11, "type": "t", "payload": '{"text": "А"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 1),
    }
    sc = NotificationsUnreadCountScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(BaseDTO(access_token=create_access_token(11, "student"))))
    assert res.count == 1


def test_mark_read_own_notification():
    db = StubDB()
    db.notifications[1] = {
        "id": 1, "user_id": 11, "type": "t", "payload": '{"text": "А"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 1),
    }
    sc = NotificationsMarkReadScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(NotificationsMarkReadDTO(
        access_token=create_access_token(11, "student"), notification_id=1,
    )))
    assert res.ok is True
    assert db.notifications[1]["read_at"] is not None


def test_mark_read_foreign_notification_forbidden():
    db = StubDB()
    db.notifications[1] = {
        "id": 1, "user_id": 99, "type": "t", "payload": '{"text": "А"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 1),
    }
    sc = NotificationsMarkReadScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(NotFoundError):
        run(sc.execute(NotificationsMarkReadDTO(
            access_token=create_access_token(11, "student"), notification_id=1,
        )))
    assert db.notifications[1]["read_at"] is None


def _seed_notifications(db):
    db.notifications[1] = {
        "id": 1, "user_id": 11, "type": "t", "payload": '{"text": "А"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 1),
    }
    db.notifications[2] = {
        "id": 2, "user_id": 11, "type": "t", "payload": '{"text": "Б"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 2),
    }
    db.notifications[3] = {
        "id": 3, "user_id": 11, "type": "t", "payload": '{"text": "В"}',
        "read_at": datetime.datetime(2030, 1, 3), "created_at": datetime.datetime(2030, 1, 3),
    }
    db.notifications[4] = {
        "id": 4, "user_id": 99, "type": "t", "payload": '{"text": "Чужое"}',
        "read_at": None, "created_at": datetime.datetime(2030, 1, 4),
    }


def test_read_all_marks_only_own_unread():
    db = StubDB()
    _seed_notifications(db)
    sc = NotificationsReadAllScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(BaseDTO(access_token=create_access_token(11, "student"))))
    assert res.updated == 2
    assert db.notifications[1]["read_at"] is not None
    assert db.notifications[2]["read_at"] is not None
    # Уже прочитанное и чужое не трогаем.
    assert db.notifications[3]["read_at"] == datetime.datetime(2030, 1, 3)
    assert db.notifications[4]["read_at"] is None


def test_read_all_idempotent():
    db = StubDB()
    _seed_notifications(db)
    sc = NotificationsReadAllScenario(db=db, metrics=DummyMetrics())
    token = create_access_token(11, "student")
    assert run(sc.execute(BaseDTO(access_token=token))).updated == 2
    assert run(sc.execute(BaseDTO(access_token=token))).updated == 0
    # После read-all счётчик непрочитанных обнуляется.
    cnt = run(NotificationsUnreadCountScenario(db=db, metrics=DummyMetrics())
              .execute(BaseDTO(access_token=token)))
    assert cnt.count == 0


def test_student_create_notifies_tutor():
    db = CaptureStub()
    seed_pair(db, rate=1500, discount=0)
    day = dt(4, 10)
    db.bookings.append({
        "id": 1, "tutor_id": 42, "weekday": WEEKDAYS[day.weekday()],
        "start_time": datetime.time(8, 0), "end_time": datetime.time(18, 0),
        "access_rule": "EVERYONE", "access_targets": None,
    })
    sc = StudentCreateLessonScenario(db=db, metrics=DummyMetrics())
    run(sc.execute(StudentCreateLessonDTO(
        access_token=create_access_token(11, "student"), tutor_user_id=7,
        start_time=iso(4, 10), end_time=iso(4, 11),
    )))
    assert db.notifications_created
    n = db.notifications_created[0]
    assert n["user_id"] == 7
    assert n["type"] == "lesson_booked"
    assert "записался" in n["payload"]


def test_set_payment_notifies_student():
    db = CaptureStub()
    seed_pair(db)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": dt(10, 10), "end_time": dt(10, 11),
        "is_group": False, "status": "SCHEDULED",
    }
    db.participants[501] = {
        "id": 501, "lesson_id": 1, "student_id": 5, "participant_settings": None,
    }
    sc = TutorSetPaymentScenario(db=db, metrics=DummyMetrics())
    run(sc.execute(TutorSetPaymentDTO(
        access_token=create_access_token(7, "tutor"),
        lesson_id=1, student_user_id=11, paid=True,
    )))
    assert db.notifications_created
    n = db.notifications_created[0]
    assert n["user_id"] == 11
    assert n["type"] == "payment_updated"
    assert "оплачено" in n["payload"]
