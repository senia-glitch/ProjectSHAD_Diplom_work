# Тесты удаления аккаунта и компенсации регистрации.
# Запуск: pytest tests/test_account_lifecycle.py -q
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ConflictError, ValidationError
from core.utils.security import create_access_token

from app.scenarios.users.delete_me import DeleteMeDTO, DeleteMeScenario
from app.scenarios.users.register import RegisterUserDTO, RegisterUserScenario
from app.scenarios.users.update_me import UpdateMeDTO, UpdateMeScenario
from app.scenarios.admin.users import AdminUpdateUserDTO, AdminUpdateUserScenario


def run(coro):
    return asyncio.run(coro)


class M:
    async def record(self, *a, **k):
        return None


class LifecycleStubDB:
    """Remove-подобный stub: хранит таблицы в dict и логирует delete-операции."""

    def __init__(self, role_name="student", admin_count=2):
        self.students = [{"id": 5, "user_id": 3}]
        self.tutors = []
        self.admins = [{"id": 9, "user_id": 3}, {"id": 10, "user_id": 4}] if admin_count > 1 else [{"id": 9, "user_id": 3}]
        self.participants = [{"id": 600, "lesson_id": 900, "student_id": 5}]
        self.configurations = [{"id": 77, "student_id": 5, "tutor_id": 42}]
        self.student_settings = [{"id": 7, "student_id": 5}]
        self.tutor_settings = []
        self.lessons = []
        self.bookings = []
        self.notifications = [{"id": 1001, "user_id": 3, "type": "lesson_added", "payload": None}]
        self.users = [{"id": 3, "role_id": 1, "username": "u1", "full_name": "U", "email": "u@x.ru",
                       "personal_number": "IND-AAAAAA01", "password_hash": "x",
                       "created_at": None, "refresh_token": None, "gender": None, "additional_info": None}]
        self.roles = [{"id": 1, "name": role_name}]
        self.log = []

    async def read(self, table, rid):
        table_map = {"users": self.users, "students": self.students, "tutors": self.tutors, "admins": self.admins}
        for row in table_map.get(table, []):
            if row["id"] == rid:
                return dict(row)
        return None

    async def query(self, sql, params, **kwargs):
        if '"roles"' in sql:
            return [{"id": 1, "name": self.roles[0]["name"]}]
        if '"admins"' in sql and ("COUNT(*)" in sql or "count" in sql.lower()):
            return [{"cnt": len(self.admins)}]
        if 'DELETE FROM "notifications"' in sql:
            self.log.append(("notifications", params.get("uid")))
            self.notifications = [n for n in self.notifications if n["user_id"] != params.get("uid")]
            return []
        if 'DELETE FROM "lesson_participants"' in sql:
            before = len(self.participants)
            self.participants = [p for p in self.participants if p["student_id"] != params.get("sid")]
            self.log.append(("lesson_participants", before - len(self.participants)))
            return []
        if 'DELETE FROM "configurations"' in sql:
            self.configurations = [c for c in self.configurations if params.get("sid") and c.get("student_id") == params["sid"]
                                   or params.get("tid") and c.get("tutor_id") == params["tid"]]
            self.log.append(("configurations", None))
            return []
        if 'DELETE FROM "student_settings"' in sql:
            self.student_settings = [s for s in self.student_settings if s["student_id"] != params.get("sid")]
            self.log.append(("student_settings", None))
            return []
        if 'DELETE FROM "tutor_settings"' in sql:
            self.tutor_settings = [t for t in self.tutor_settings if t["tutor_id"] != params.get("tid")]
            self.log.append(("tutor_settings", None))
            return []
        if 'DELETE FROM "lessons"' in sql:
            self.lessons = [l for l in self.lessons if l["tutor_id"] != params.get("tid")]
            self.log.append(("lessons", None))
            return []
        if 'DELETE FROM "bookings"' in sql:
            self.bookings = [b for b in self.bookings if b["tutor_id"] != params.get("tid")]
            self.log.append(("bookings", None))
            return []
        if 'DELETE FROM "students" WHERE' in sql:
            self.students = [s for s in self.students if s["id"] != params.get("pid")]
            self.log.append(("students", None))
            return []
        if 'DELETE FROM "tutors" WHERE' in sql:
            self.tutors = [t for t in self.tutors if t["id"] != params.get("pid")]
            self.log.append(("tutors", None))
            return []
        if '"students"' in sql and "user_id" in sql:
            return [{"id": s["id"]} for s in self.students if s.get("user_id") == params.get("uid")]
        if '"tutors"' in sql and "user_id" in sql:
            return [{"id": t["id"]} for t in self.tutors if t.get("user_id") == params.get("uid")]
        if '"admins"' in sql and "user_id" in sql:
            return [{"id": a["id"]} for a in self.admins if a.get("user_id") == params.get("uid")]
        if '"tutor_settings"' in sql:
            return [dict(s) for s in self.tutor_settings if s["tutor_id"] == params.get("tid")]
        return []

    async def create(self, table, data):
        table_map = {"users": self.users, "students": self.students, "tutors": self.tutors,
                     "student_settings": self.student_settings, "tutor_settings": self.tutor_settings}
        row = {**data, "id": 1000 + len(self.log)}
        table_map[table].append(row)
        return dict(row)

    async def update(self, table, rid, data):
        table_map = {"users": self.users, "student_settings": self.student_settings,
                     "tutor_settings": self.tutor_settings}
        for row in table_map.get(table, []):
            if row["id"] == rid:
                row.update(data)
                return dict(row)
        return {}

    async def delete(self, table, rid):
        table_map = {"users": "users", "students": "students", "tutors": "tutors",
                     "admins": "admins", "lesson_participants": "participants",
                     "configurations": "configurations"}
        attr = table_map[table]
        rows = getattr(self, attr)
        before = len(rows)
        setattr(self, attr, [r for r in rows if r["id"] != rid])
        removed = before - len(getattr(self, attr))
        self.log.append((f"delete:{table}", removed))
        return removed > 0


# ---套餐 2: уведомления чистятся до удаления users ---


def test_delete_student_also_purges_notifications():
    db = LifecycleStubDB(role_name="student")
    sc = DeleteMeScenario(db=db, metrics=M())
    res = run(sc.execute(DeleteMeDTO(access_token=create_access_token(3, "student"))))
    assert res.ok
    assert ("notifications", 3) in db.log, "DELETE notifications не выполнен"
    assert db.notifications == []
    # порядок: notifications были до удаления users
    order = [entry[0] for entry in db.log]
    assert order.index("notifications") < next(
        i for i, entry in enumerate(db.log) if entry[0] == "delete:users"
    )
    assert db.users == [], "user должен быть удалён"


def test_delete_tutor_purges_notifications_and_cascade():
    stub = LifecycleStubDB(role_name="tutor")
    stub.tutors = [{"id": 5, "user_id": 3}]
    stub.lessons = [{"id": 900, "tutor_id": 5, "start_time": "x", "end_time": "y", "status": "SCHEDULED"}]
    sc = DeleteMeScenario(db=stub, metrics=M())
    res = run(sc.execute(DeleteMeDTO(access_token=create_access_token(3, "tutor"))))
    assert res.ok
    assert ("notifications", 3) in stub.log
    assert stub.notifications == []
    assert stub.tutors == []
    assert stub.users == []


def test_delete_last_admin_conflict():
    db = LifecycleStubDB(role_name="admin", admin_count=1)
    sc = DeleteMeScenario(db=db, metrics=M())
    with pytest.raises(ConflictError):
        run(sc.execute(DeleteMeDTO(access_token=create_access_token(3, "admin"))))
    assert ("delete:admins", 1) not in db.log  # удаление профиля запрещено
    assert db.users != [], "никого не удаляли"


def test_delete_admin_with_second_admin_allowed():
    db = LifecycleStubDB(role_name="admin", admin_count=2)
    sc = DeleteMeScenario(db=db, metrics=M())
    res = run(sc.execute(DeleteMeDTO(access_token=create_access_token(3, "admin"))))
    assert res.ok
    assert db.admins == [{"id": 10, "user_id": 4}]
    assert db.users == []


# ---套餐 7: компенсация регистрации откатывает созданный профиль ---


class RegisterSeedDB(LifecycleStubDB):
    def __init__(self):
        super().__init__()
        self.students = []
        self.tutors = []
        self.admins = []
        self.notifications = []
        self.users = []
        self.student_settings = []
        self.tutor_settings = []


class FlakySettingsStubDB(RegisterSeedDB):
    """create(student_settings) падает."""

    async def create(self, table, data):
        if table == "student_settings":
            raise RuntimeError("db down between creates")
        return await super().create(table, data)


def test_register_compensation_deletes_profile_and_user():
    db = FlakySettingsStubDB()
    sc = RegisterUserScenario(db=db, metrics=M())
    with pytest.raises(RuntimeError):
        run(sc.execute(RegisterUserDTO(
            role="student", username="user1", password="12345678",
            full_name="U", email="u@x.ru",
        )))
    assert ("students", None) in [(name, arg) for name, arg in [(e[0], e[1]) for e in db.log]], \
        f"профиль students должен быть откачен: {db.log}"
    assert db.students == [], "профиль остался в БД (сирота)"
    assert db.users == [], "users должен быть удалён компенсацией"
    assert db.student_settings == []


def test_register_failure_before_profile_deletes_user():
    class FailStudentsDB(RegisterSeedDB):
        async def create(self, table, data):
            if table == "students":
                raise RuntimeError("boom")
            return await LifecycleStubDB.create(self, table, data)

    db = FailStudentsDB()
    sc = RegisterUserScenario(db=db, metrics=M())
    with pytest.raises(RuntimeError):
        run(sc.execute(RegisterUserDTO(
            role="student", username="user1", password="12345678",
            full_name="U", email="u@x.ru",
        )))
    assert db.users == [], "users удалён компенсацией (профиль не создавался)"
    assert db.students == []


# ---套餐 3/11: контракт admin-update и запрет пустого имени ---


def test_admin_dto_target_user_id_optional():
    dto = AdminUpdateUserDTO(access_token="x", full_name="Иван")
    assert dto.target_user_id is None
    db = LifecycleStubDB()
    sc = AdminUpdateUserScenario(db=db, metrics=M())
    dto.access_token = create_access_token(1, "admin")
    with pytest.raises(ValidationError):
        run(sc.execute(dto))


def test_update_me_rejects_blank_name():
    with pytest.raises(Exception):
        UpdateMeDTO(access_token="x", full_name="   ")
    UpdateMeDTO(access_token="x", full_name="Иван  ")
