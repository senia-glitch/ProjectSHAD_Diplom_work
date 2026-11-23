# Тесты мульти-сессий refresh-токенов. Запуск: pytest tests/test_refresh_sessions.py -q
import asyncio
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ValidationError
from core.utils.security import create_refresh_token

from app.utils.tokens import (
    MAX_REFRESH_SESSIONS,
    hash_refresh_token,
    parse_refresh_hashes,
    rotate_refresh_store,
)
from app.scenarios.auth.login import LoginDTO, LoginScenario
from app.scenarios.auth.refresh import RefreshDTO, RefreshScenario
from app.scenarios.auth.logout import LogoutDTO, LogoutScenario
from app.scenarios.users.register import RegisterUserDTO, RegisterUserScenario


def run(coro):
    return asyncio.run(coro)


class M:
    async def record(self, *a, **k):
        return None


class AuthStubDB:
    """Stub users/roles с фиксацией update("users") вызовов."""

    def __init__(self, user_row):
        self.user = dict(user_row)
        self.users = {self.user.get("username", "u1"): self.user}
        self.updates = []

    async def read(self, table, rid):
        return dict(self.user) if rid == self.user.get("id") else None

    async def query(self, sql, params):
        if '"roles"' in sql:
            return [{"id": 1, "name": "student"}]
        if '"users"' in sql and "username" in sql:
            user = self.users.get(params.get("username"))
            return [dict(user)] if user else []
        return []

    async def create(self, table, data):
        if table == "users":
            self.user.update({**data, "id": 3})
            self.users[self.user.get("username", "u1")] = dict(self.user)
            return dict(self.user)
        if table == "students":
            return {"id": 5}
        if table == "student_settings":
            return {"id": 7}
        raise AssertionError(table)

    async def update(self, table, rid, data):
        self.updates.append(dict(data))
        self.user.update(data)
        return {**self.user, "id": rid}

    async def delete(self, table, rid):
        self.updates.append({"delete": (table, rid)})
        return True


RAW_USER = {
    "id": 3, "role_id": 1, "username": "u1", "personal_number": "IND-AAAAAA01",
    "password_hash": "x", "full_name": "U", "email": "u@x.ru",
    "refresh_token": None,
}


def fresh_store(user_id: int, token: str) -> str:
    return json.dumps([hash_refresh_token(token)])


def test_parse_legacy_single_hash():
    assert parse_refresh_hashes("abcdef") == ["abcdef"]
    assert parse_refresh_hashes(None) == []
    assert parse_refresh_hashes(json.dumps(["a", "b"])) == ["a", "b"]


def test_store_rotation_keeps_other_sessions_and_evicts_oldest():
    hashes = [f"n{i}" for i in range(6)]
    store = json.dumps(hashes)
    rotated = rotate_refresh_store(store, "n2", "new1")
    assert rotated[0] == "new1"
    assert "n2" not in rotated
    assert len(rotated) == MAX_REFRESH_SESSIONS  # лимит выдержан
    assert "n0" in rotated and "n4" in rotated   # старые на месте
    assert "n5" not in rotated  # самая старая сессия вытеснена лимитом


async def _login_db():
    from core.utils.security import hash_password
    db = AuthStubDB({**RAW_USER, "password_hash": await hash_password("12345678")})
    return db


def test_login_writes_single_session_store():
    db = run(_login_db())
    sc = LoginScenario(db=db, metrics=M())
    res = run(sc.execute(LoginDTO(username="u1", password="12345678")))
    stored = db.user["refresh_token"]
    assert stored.startswith("[")
    assert hash_refresh_token(res.refresh_token) in json.loads(stored)


def test_register_writes_session_store():
    db = AuthStubDB({**RAW_USER, "refresh_token": None})
    sc = RegisterUserScenario(db=db, metrics=M())
    res = run(sc.execute(RegisterUserDTO(
        role="student", username="user1", password="12345678",
        full_name="U", email="u@x.ru",
    )))
    stored = db.user["refresh_token"]
    assert stored.startswith("[")
    assert hash_refresh_token(res.refresh_token) in json.loads(stored)


def test_refresh_rotates_own_session_keeps_other():
    db = AuthStubDB(RAW_USER)
    token_a = create_refresh_token(3)
    token_b = create_refresh_token(3)
    db.user["refresh_token"] = json.dumps([hash_refresh_token(token_a), hash_refresh_token(token_b)])

    sc = RefreshScenario(db=db, metrics=M())
    res = run(sc.execute(RefreshDTO(refresh_token=token_a)))
    stored = json.loads(db.user["refresh_token"])
    assert hash_refresh_token(res.refresh_token) in stored
    assert stored[0] == hash_refresh_token(res.refresh_token)  # ротирован на первое место
    assert hash_refresh_token(token_a) not in stored, "старый хэш отозван"
    assert hash_refresh_token(token_b) in stored, "другая сессия жива"


def test_parallel_refresh_of_same_token_revokes_fast():
    # Пере-.choice: один и тот же токен в двух вкладках: первая ротация
    # отзывает общий хэш; вторая получает явный 422 сразу (одна сессия —
    # один хэш по принятой модели).
    db = AuthStubDB(RAW_USER)
    token = create_refresh_token(3)
    db.user["refresh_token"] = fresh_store(3, token)

    async def scenario():
        sc = RefreshScenario(db=db, metrics=M())
        outcomes = []

        async def do_refresh():
            try:
                outcomes.append(("ok", (await sc.execute(RefreshDTO(refresh_token=token))).refresh_token))
            except Exception as e:  # noqa: BLE001
                outcomes.append(("fail", type(e).__name__))

        await asyncio.gather(do_refresh(), do_refresh())
        return outcomes

    outcomes = asyncio.run(scenario())
    ok = [o for o in outcomes if o[0] == "ok"]
    assert len(ok) == 1, outcomes
    stored = db.user["refresh_token"]
    # единственный хэш в БД — от успешной ротации
    stored_hashes = json.loads(stored)
    assert stored_hashes == [hash_refresh_token(ok[0][1])]
    assert hash_refresh_token(token) not in stored_hashes


def test_refresh_revoked_when_not_in_store():
    db = AuthStubDB(RAW_USER)
    token = create_refresh_token(3)
    db.user["refresh_token"] = json.dumps([hash_refresh_token("something_else")])
    sc = RefreshScenario(db=db, metrics=M())
    with pytest.raises(ValidationError):
        run(sc.execute(RefreshDTO(refresh_token=token)))


def test_logout_removes_only_own_session():
    db = AuthStubDB(RAW_USER)
    token_a = create_refresh_token(3)
    token_b = create_refresh_token(3)
    db.user["refresh_token"] = json.dumps([hash_refresh_token(token_a), hash_refresh_token(token_b)])

    sc = LogoutScenario(db=db, metrics=M())
    res = run(sc.execute(LogoutDTO(refresh_token=token_a)))
    assert res.ok
    still = json.loads(db.user["refresh_token"])
    assert hash_refresh_token(token_a) not in still
    assert hash_refresh_token(token_b) in still


def test_logout_with_stale_token_allows_valid_session():
    # Logout с токеном, которого нет в списке: сессия остаётся без изменений.
    db = AuthStubDB(RAW_USER)
    db.user["refresh_token"] = fresh_store(3, create_refresh_token(3))
    before = db.user["refresh_token"]
    sc = LogoutScenario(db=db, metrics=M())
    run(sc.execute(LogoutDTO(refresh_token=create_refresh_token(3))))
    assert db.user["refresh_token"] == before
