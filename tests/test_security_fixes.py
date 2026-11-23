# Тесты исправлений безопасности и корректности:
# H2 (мутации через write-канал), H3 (IDOR в уроках репетитора),
# M2 (aware->серверное время), M4 (валидация эффективного интервала),
# M5 (дедлайн отмены), M6 (join только доступных уроков), M3 (DTO-ограничения).
# Запуск: pytest tests/test_security_fixes.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.utils.security import create_access_token
from core import ValidationError, ConflictError
from app.core.exceptions import ForbiddenError
from app.utils.safe_parse import parse_iso_datetime
from app.scenarios.student.lessons import (
    StudentGetTutorLessonsDTO, StudentGetTutorLessonsScenario,
    StudentJoinLessonDTO, StudentJoinLessonScenario,
    StudentLeaveLessonDTO, StudentLeaveLessonScenario,
)
from app.scenarios.tutor.lessons import (
    TutorUpdateLessonDTO, TutorUpdateLessonScenario,
)
from app.scenarios.users.delete_me import (
    DeleteMeDTO, DeleteMeScenario,
)


def run(coro):
    return asyncio.run(coro)


def student_token(uid=11):
    return create_access_token(uid, "student")


def tutor_token(uid=7):
    return create_access_token(uid, "tutor")


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    """Гибкий стаб с журналом запросов (для проверки channel='write')."""

    def __init__(self):
        self.users = {}            # user_id -> row
        self.roles = {}            # role_id -> name
        self.students = {}         # user_id -> student_id
        self.tutors = {}           # user_id -> tutor_id
        self.configs = []          # configuration rows
        self.tutor_settings = {}   # tutor_id -> row
        self.lessons = {}          # id -> row
        self.participants = {}     # id -> row
        self.query_log = []        # (sql, params, kwargs)
        self._next_part = 500

    async def query(self, sql, params, **kwargs):
        self.query_log.append((sql, dict(params), dict(kwargs)))
        if '"roles"' in sql:
            rid = params.get("role_id")
            if rid in self.roles:
                return [{"id": rid, "name": self.roles[rid]}]
            return []
        if '"tutors"' in sql and '"configurations"' not in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        if '"students"' in sql and '"configurations"' not in sql:
            uid = params.get("uid")
            return [{"id": self.students[uid]}] if uid in self.students else []
        if '"tutor_settings"' in sql:
            tid = params.get("tid")
            return [dict(self.tutor_settings[tid])] if tid in self.tutor_settings else []
        if '"configurations"' in sql:
            return [dict(c) for c in self.configs
                    if (params.get("sid") is None or c["student_id"] == params.get("sid"))
                    and (params.get("tid") is None or c["tutor_id"] == params.get("tid"))]
        if '"lesson_participants"' in sql:
            rows = [dict(p) for p in self.participants.values()]
            if params.get("lid") is not None:
                rows = [p for p in rows if p["lesson_id"] == params["lid"]]
            if params.get("sid") is not None:
                rows = [p for p in rows if p["student_id"] == params["sid"]]
            return rows
        if '"lessons"' in sql:
            rows = [dict(l) for l in self.lessons.values()]
            if params.get("tid") is not None:
                rows = [l for l in rows if l["tutor_id"] == params["tid"]]
            lid = params.get("lid")
            if lid is not None and "start_time <" not in sql and "start_time >=" not in sql:
                # Точечная выборка по id.
                return [l for l in rows if l["id"] == lid]
            # Список/пагинация (временные предикаты здесь не эмулируем —
            # покрываемые тесты их не используют).
            off = params.get("off") or 0
            lim = params.get("lim")
            rows = rows[off:] if lim is None else rows[off:off + lim]
            return rows
        return []

    async def create(self, table, data, **kwargs):
        if table == "lesson_participants":
            self._next_part += 1
            row = {"id": self._next_part, **data}
            self.participants[row["id"]] = row
            return dict(row)
        raise AssertionError(table)

    async def update(self, table, rid, data, **kwargs):
        store = self.lessons if table == "lessons" else self.participants
        store[rid].update(data)
        return dict(store[rid])

    async def read(self, table, rid, **kwargs):
        if table == "users":
            return dict(self.users[rid]) if rid in self.users else None
        store = self.lessons if table == "lessons" else self.participants
        return dict(store[rid])

    async def delete(self, table, rid, **kwargs):
        stores = {
            "users": self.users,
            "students": {s: {"id": s} for s in self.students.values()},
            "tutors": {t: {"id": t} for t in self.tutors.values()},
        }
        if table in stores:
            stores[table].pop(rid, None)
            return True
        store = self.lessons if table == "lessons" else self.participants
        store.pop(rid, None)
        return True


def seed_pair(db, allow_self_booking=True, booking_lead=0, cancel_lead=0, mode="YES"):
    db.roles[1] = "student"
    db.roles[2] = "tutor"
    db.users[11] = {"id": 11, "role_id": 1}
    db.users[7] = {"id": 7, "role_id": 2}
    db.students[11] = 5
    db.tutors[7] = 42
    db.tutor_settings[42] = {
        "tutor_id": 42, "self_booking_mode": mode, "self_booking_whitelist": None,
    }
    db.configs.append({
        "id": 77, "student_id": 5, "tutor_id": 42,
        "hourly_rate": 2000, "discount": 0,
        "allow_self_booking": allow_self_booking,
        "booking_lead_time_hours": booking_lead,
        "cancellation_lead_time_hours": cancel_lead,
    })


def test_tutor_lessons_require_configuration():
    db = StubDB()
    seed_pair(db)
    db.configs.clear()
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11), "is_group": True,
        "status": "SCHEDULED", "lesson_links": None,
    }
    sc = StudentGetTutorLessonsScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ForbiddenError):
        run(sc.execute(StudentGetTutorLessonsDTO(
            access_token=student_token(), tutor_user_id=7)))


def test_tutor_lessons_with_configuration_ok():
    db = StubDB()
    seed_pair(db)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11), "is_group": True,
        "status": "SCHEDULED", "lesson_links": None,
    }
    sc = StudentGetTutorLessonsScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentGetTutorLessonsDTO(
        access_token=student_token(), tutor_user_id=7)))
    assert [l.lesson_id for l in res.lessons] == [1]


def test_join_individual_forbidden():
    db = StubDB()
    seed_pair(db)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11), "is_group": False,
        "status": "SCHEDULED",
    }
    sc = StudentJoinLessonScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ForbiddenError):
        run(sc.execute(StudentJoinLessonDTO(
            access_token=student_token(), lesson_id=1)))


def test_join_group_ok():
    db = StubDB()
    seed_pair(db)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11), "is_group": True,
        "status": "SCHEDULED",
    }
    sc = StudentJoinLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentJoinLessonDTO(
        access_token=student_token(), lesson_id=1)))
    assert res.participant_id


def test_join_denied_when_self_booking_off():
    db = StubDB()
    seed_pair(db, allow_self_booking=False)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": datetime.datetime(2030, 6, 1, 10),
        "end_time": datetime.datetime(2030, 6, 1, 11), "is_group": True,
        "status": "SCHEDULED",
    }
    sc = StudentJoinLessonScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ForbiddenError):
        run(sc.execute(StudentJoinLessonDTO(
            access_token=student_token(), lesson_id=1)))


def test_leave_after_deadline_forbidden():
    db = StubDB()
    seed_pair(db, cancel_lead=24)
    start = datetime.datetime.now() + datetime.timedelta(hours=1)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": start,
        "end_time": start + datetime.timedelta(hours=1), "is_group": True,
        "status": "SCHEDULED",
    }
    db.participants[501] = {
        "id": 501, "lesson_id": 1, "student_id": 5, "participant_settings": None,
    }
    sc = StudentLeaveLessonScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(StudentLeaveLessonDTO(
            access_token=student_token(), lesson_id=1)))


def test_leave_before_deadline_ok():
    db = StubDB()
    seed_pair(db, cancel_lead=24)
    start = datetime.datetime.now() + datetime.timedelta(hours=48)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": start,
        "end_time": start + datetime.timedelta(hours=1), "is_group": True,
        "status": "SCHEDULED",
    }
    db.participants[501] = {
        "id": 501, "lesson_id": 1, "student_id": 5, "participant_settings": None,
    }
    sc = StudentLeaveLessonScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(StudentLeaveLessonDTO(
        access_token=student_token(), lesson_id=1)))
    assert res.ok is True


def test_update_single_bound_to_past_rejected():
    db = StubDB()
    db.tutors[7] = 42
    start = datetime.datetime.now() + datetime.timedelta(days=2)
    db.lessons[1] = {
        "id": 1, "tutor_id": 42, "start_time": start,
        "end_time": start + datetime.timedelta(hours=1), "is_group": False,
        "status": "SCHEDULED",
    }
    sc = TutorUpdateLessonScenario(db=db, metrics=DummyMetrics())
    past = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()
    with pytest.raises(ValidationError):
        run(sc.execute(TutorUpdateLessonDTO(
            access_token=tutor_token(), lesson_id=1, start_time=past)))


def test_aware_datetime_converted_to_server_local():
    import datetime as dtmod
    local_offset = dtmod.datetime.now().astimezone().utcoffset()
    # Вход со смещением, заведомо отличным от локального.
    other_offset = datetime.timedelta(hours=(local_offset.total_seconds() // 3600) + 7)
    sign = "+" if other_offset >= datetime.timedelta(0) else "-"
    total = abs(int(other_offset.total_seconds() // 60))
    off_str = f"{sign}{total // 60:02d}:{total % 60:02d}"
    aware = dtmod.datetime.fromisoformat(f"2030-01-01T12:00:00{off_str}")
    got = parse_iso_datetime(f"2030-01-01T12:00:00{off_str}", "start_time")
    assert got.tzinfo is None
    assert got == aware.astimezone().replace(tzinfo=None)
    # И это не наивное отбрасывание смещения.
    assert got != dtmod.datetime(2030, 1, 1, 12, 0)


def test_delete_me_uses_write_channel():
    db = StubDB()
    db.roles[1] = "student"
    db.users[11] = {"id": 11, "role_id": 1}
    db.students[11] = 5
    sc = DeleteMeScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(DeleteMeDTO(access_token=student_token())))
    assert res.ok is True
    deletes = [(sql, kw) for (sql, _p, kw) in db.query_log
               if sql.strip().upper().startswith("DELETE")]
    assert deletes, "ожидались DELETE-запросы"
    assert all(kw.get("channel") == "write" for (_sql, kw) in deletes)


def test_dto_limits_reject_bad_tariffs():
    from pydantic import ValidationError as PydanticValidationError
    from app.scenarios.tutor.profile import TutorUpdateMySettingsDTO
    from app.scenarios.tutor.configurations import TutorUpdateConfigurationDTO
    with pytest.raises(PydanticValidationError):
        TutorUpdateMySettingsDTO(access_token="x", discount=150.0)
    with pytest.raises(PydanticValidationError):
        TutorUpdateMySettingsDTO(access_token="x", hourly_rate=-1.0)
    with pytest.raises(PydanticValidationError):
        TutorUpdateConfigurationDTO(access_token="x", slot_step_minutes=0)
    # Корректные значения проходят.
    TutorUpdateMySettingsDTO(access_token="x", discount=10.0)
    TutorUpdateConfigurationDTO(access_token="x", slot_step_minutes=60)


def test_password_over_72_bytes_rejected_at_dto():
    from pydantic import ValidationError as PydanticValidationError
    from app.scenarios.users.register import RegisterUserDTO
    from app.scenarios.auth.login import LoginDTO
    from app.scenarios.users.change_password import ChangePasswordDTO
    long_pw = "a" * 100
    long_unicode = "я" * 40  # 80 байт в UTF-8
    with pytest.raises(PydanticValidationError):
        RegisterUserDTO(role="student", username="user1", password=long_pw,
                        full_name="N", email="a@b.cc")
    with pytest.raises(PydanticValidationError):
        LoginDTO(username="user1", password=long_pw)
    with pytest.raises(PydanticValidationError):
        ChangePasswordDTO(access_token="x", old_password="oldpass12", new_password=long_pw)
    with pytest.raises(PydanticValidationError):
        RegisterUserDTO(role="student", username="user1", password=long_unicode,
                        full_name="N", email="a@b.cc")
    # Граница 72 байта проходит валидацию DTO.
    RegisterUserDTO(role="student", username="user1", password="a" * 72,
                    full_name="N", email="a@b.cc")


def test_update_me_duplicate_email_conflict():
    from app.scenarios.users.update_me import UpdateMeDTO, UpdateMeScenario

    class DupDB(StubDB):
        async def read(self, table, rid, **kwargs):
            if table == "users":
                return {"id": 11, "role_id": 1}
            return await super().read(table, rid, **kwargs)

        async def update(self, table, rid, data, **kwargs):
            raise Exception('duplicate key value violates unique constraint "users_email_key"')

    db = DupDB()
    sc = UpdateMeScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ConflictError):
        run(sc.execute(UpdateMeDTO(access_token=student_token(), email="taken@x.yy")))
