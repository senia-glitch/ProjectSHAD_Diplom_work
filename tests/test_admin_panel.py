# Админ-панель владельца: вход по ключу, блокировка, доступ к БД.
# Запуск: pytest tests/test_admin_panel.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ValidationError
from core.utils.security import create_access_token

from app.api.access import authenticate
from app.core import blocklist
from app.core.exceptions import TooManyRequestsError, UnauthorizedError
from app.scenarios.admin import panel
from app.scenarios.admin.database import MASK, _cast_type, _clean_sql, _row, _text_value
from app.utils.admin_audit import KEY_PREFIX, hash_admin_key, new_admin_key


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *a, **k):
        return None


class KeyStub:
    """Минимальная БД: один администратор с ключом, журнал действий в памяти."""

    def __init__(self, key: str, blocked=False):
        self.key_hash = hash_admin_key(key)
        self.blocked = blocked
        self.audit, self.updated = [], {}

    async def query(self, sql, params, **kw):
        if 'FROM "admins" a' in sql and "key_hash = :h" in sql:
            if params["h"] == self.key_hash:
                return [{"user_id": 7, "refresh_token": None,
                         "blocked_at": datetime.datetime(2030, 1, 1) if self.blocked else None}]
            return []
        return []

    async def update(self, table, rid, data):
        self.updated[(table, rid)] = data
        return data

    async def create(self, table, data):
        assert table == "admin_audit"
        self.audit.append(data)
        return data


def test_key_format_and_hash():
    key = new_admin_key()
    assert key.startswith(KEY_PREFIX) and len(key) > 40
    assert new_admin_key() != key
    assert hash_admin_key(key) == hash_admin_key(f"  {key}\n")
    assert len(hash_admin_key(key)) == 64


def test_key_login_issues_admin_session_and_audits():
    key = new_admin_key()
    db = KeyStub(key)
    res = run(panel.AdminKeyLoginScenario(db=db, metrics=DummyMetrics()).execute(
        panel.AdminKeyLoginDTO(key=key, ip="10.0.0.1")))
    assert res.role == "admin" and res.user_id == 7 and res.access_token and res.refresh_token
    assert db.updated[("users", 7)]["refresh_token"]
    assert db.audit[-1]["action"] == "login" and db.audit[-1]["ip"] == "10.0.0.1"


def test_key_login_rejects_wrong_or_blocked_and_limits_attempts():
    key = new_admin_key()
    sc = panel.AdminKeyLoginScenario(db=KeyStub(key, blocked=True), metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(panel.AdminKeyLoginDTO(key=key, ip="10.0.0.2")))
    db = KeyStub(key)
    sc = panel.AdminKeyLoginScenario(db=db, metrics=DummyMetrics())
    for _ in range(4):
        with pytest.raises(ValidationError):
            run(sc.execute(panel.AdminKeyLoginDTO(key="shad_admin_wrong_key_value", ip="10.0.0.3")))
    with pytest.raises(ValidationError):
        run(sc.execute(panel.AdminKeyLoginDTO(key="shad_admin_wrong_key_value", ip="10.0.0.3")))
    # После 5 неудач адрес закрыт — даже верный ключ не принимается.
    with pytest.raises(TooManyRequestsError):
        run(sc.execute(panel.AdminKeyLoginDTO(key=key, ip="10.0.0.3")))
    assert any(a["action"] == "login_failed" for a in db.audit)


def test_blocked_user_is_rejected_immediately():
    policy = {"guest": frozenset(), "student": frozenset({"x"})}
    token = create_access_token(4242, "student")
    assert authenticate(f"Bearer {token}", policy)["user_id"] == 4242
    blocklist.mark_blocked(4242)
    try:
        with pytest.raises(UnauthorizedError):
            authenticate(f"Bearer {token}", policy)
    finally:
        blocklist.mark_unblocked(4242)
    assert authenticate(f"Bearer {token}", policy)["user_id"] == 4242


def test_password_login_refuses_admin_accounts():
    from app.scenarios.auth.login import LoginDTO, LoginScenario
    from core.utils.security import hash_password

    class LoginStub:
        def __init__(self, password_hash):
            self.password_hash = password_hash

        async def query(self, sql, params, **kw):
            if 'FROM "users"' in sql:
                return [{"id": 7, "role_id": 3, "password_hash": self.password_hash, "refresh_token": None}]
            if 'FROM "admins"' in sql:
                return [{"id": 1}]
            return [{"id": 3, "name": "admin"}]

    db = LoginStub(run(hash_password("owner-pass-123")))
    with pytest.raises(ValidationError):
        run(LoginScenario(db=db, metrics=DummyMetrics()).execute(LoginDTO(username="owner", password="owner-pass-123")))


def test_secret_columns_masked_and_values_plain():
    row = {"id": 1, "password_hash": "$2b$...", "created_at": datetime.datetime(2030, 1, 1, 9), "meta": {"a": 1}}
    out = _row(row, {"password_hash"})
    assert out == {"id": 1, "password_hash": MASK, "created_at": "2030-01-01T09:00:00", "meta": {"a": 1}}
    assert _row({"password_hash": None}, {"password_hash"}) == {"password_hash": None}


def test_sql_and_value_helpers():
    assert _clean_sql("  select 1 ;; ") == "select 1"
    with pytest.raises(ValidationError):
        _clean_sql(" ; ")
    assert _cast_type({"udt": "int4"}) == "int4"
    assert _cast_type({"udt": "_text"}) == "text[]"
    assert _text_value(True) == "true" and _text_value(5) == "5" and _text_value({"a": "б"}) == '{"a": "б"}'
