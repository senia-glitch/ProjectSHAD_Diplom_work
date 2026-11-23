# Тесты хранения refresh-токена: в БД хранится хэш (JSON-список сессий),
# не открытый токен. Запуск: pytest tests/test_refresh_token_storage.py -q
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core import ValidationError
from core.utils.security import create_refresh_token, hash_password
from app.utils.tokens import hash_refresh_token
from app.scenarios.auth.refresh import RefreshDTO, RefreshScenario
from app.scenarios.auth.login import LoginDTO, LoginScenario


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.users = {11: {"id": 11, "role_id": 1, "refresh_token": None}}
        self.roles = {1: {"id": 1, "name": "student"}}
        self.updated = []

    async def query(self, sql, params, **kwargs):
        if '"users"' in sql:
            username = params.get("username")
            if username is not None:
                for u in self.users.values():
                    if u.get("username") == username:
                        return [dict(u)]
                return []
        if '"roles"' in sql:
            rid = params.get("role_id")
            return [dict(self.roles[rid])] if rid in self.roles else []
        return []

    async def read(self, table, rid, **kwargs):
        if table == "users":
            return dict(self.users[rid]) if rid in self.users else None
        raise AssertionError(table)

    async def update(self, table, rid, data, **kwargs):
        if table == "users":
            self.users[rid].update(data)
            self.updated.append(dict(data))
            return dict(self.users[rid])
        raise AssertionError(table)

    async def create(self, table, data, **kwargs):
        raise AssertionError(table)

    async def delete(self, table, rid, **kwargs):
        raise AssertionError(table)


def test_hash_is_deterministic_hex():
    h1 = hash_refresh_token("token-1")
    assert h1 == hash_refresh_token("token-1")
    assert len(h1) == 64
    assert h1 != hash_refresh_token("token-2")


def test_refresh_accepts_stored_hash():
    db = StubDB()
    token = create_refresh_token(11)
    db.users[11]["refresh_token"] = hash_refresh_token(token)
    sc = RefreshScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(RefreshDTO(refresh_token=token)))
    assert res.access_token
    assert res.refresh_token
    # Новая семантика: JSON-список хэшей сессий, ротация отзывает свой хэш.
    assert json.loads(db.users[11]["refresh_token"]) == [hash_refresh_token(res.refresh_token)]


def test_refresh_rejects_plaintext_storage():
    db = StubDB()
    token = create_refresh_token(11)
    db.users[11]["refresh_token"] = token
    sc = RefreshScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(RefreshDTO(refresh_token=token)))


def test_login_stores_hash():
    db = StubDB()
    db.users[11]["username"] = "student1"
    db.users[11]["password_hash"] = run(hash_password("Secret-123"))
    sc = LoginScenario(db=db, metrics=DummyMetrics())
    res = run(sc.execute(LoginDTO(username="student1", password="Secret-123")))
    assert res.refresh_token
    stored = db.users[11]["refresh_token"]
    assert stored.startswith("[")
    assert json.loads(stored) == [hash_refresh_token(res.refresh_token)]
    assert res.refresh_token not in stored  # в БД хэш, не открытый токен