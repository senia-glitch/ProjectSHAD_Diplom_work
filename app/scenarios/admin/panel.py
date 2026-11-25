"""Админ-панель владельца: вход по ключу, сводка, журнал действий, управление пользователями.

Вход администратора — только по уникальному ключу (в БД хранится SHA-256). Неудачные попытки
ограничены по адресу клиента. Каждое действие администратора пишется в admin_audit.
"""
import datetime
import secrets
import string

from pydantic import BaseModel, Field
from core import BaseScenario, ConflictError, NotFoundError, ValidationError, register_scenario
from core.dto import BaseDTO
from core.utils.security import create_access_token, create_refresh_token, hash_password

from app.core import blocklist
from app.core.exceptions import TooManyRequestsError
from app.realtime.guard import FailureTracker
from app.scenarios.users.delete_me import delete_user_data
from app.utils.admin_audit import audit, hash_admin_key, new_admin_key
from app.utils.clock import utc_now
from app.utils.json_codec import parse_value
from app.utils.tokens import create_refresh_store, hash_refresh_token

# 5 неудачных попыток за 15 минут — адрес закрыт на 15 минут.
_key_failures = FailureTracker(5, 15 * 60, 15 * 60)


# ---------- вход по ключу ----------

class AdminKeyLoginDTO(BaseModel):
    key: str = Field(min_length=10, max_length=200)
    ip: str | None = None


class AdminKeyLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    role: str


@register_scenario("admin_key_login", dto=AdminKeyLoginDTO, response=AdminKeyLoginResponse)
class AdminKeyLoginScenario(BaseScenario):
    async def execute(self, dto: AdminKeyLoginDTO) -> AdminKeyLoginResponse:
        ip = dto.ip or "unknown"
        if _key_failures.retry_after(ip) > 0:
            raise TooManyRequestsError("Too many attempts, try later")
        rows = await self._db.query(
            'SELECT a.user_id, u.refresh_token, u.blocked_at FROM "admins" a '
            'JOIN "users" u ON u.id = a.user_id WHERE a.key_hash = :h',
            {"h": hash_admin_key(dto.key)},
        )
        if not rows or rows[0].get("blocked_at"):
            _key_failures.fail(ip)
            await audit(self._db, None, "login_failed", details={"reason": "bad_key"}, ip=ip)
            raise ValidationError("Invalid admin key")
        user_id = rows[0]["user_id"]
        access = create_access_token(user_id, "admin")
        refresh = create_refresh_token(user_id)
        await self._db.update("users", user_id, {
            "refresh_token": create_refresh_store(rows[0].get("refresh_token"), hash_refresh_token(refresh)),
        })
        await audit(self._db, user_id, "login", ip=ip)
        return AdminKeyLoginResponse(access_token=access, refresh_token=refresh, user_id=user_id, role="admin")


class AdminActorDTO(BaseModel):
    actor_id: int
    ip: str | None = None


class AdminKeyResponse(BaseModel):
    key: str
    created_at: str


@register_scenario("admin_rotate_key", dto=AdminActorDTO, response=AdminKeyResponse)
class AdminRotateKeyScenario(BaseScenario):
    """Новый ключ владельца; старый сразу перестаёт действовать. Показывается один раз."""

    async def execute(self, dto: AdminActorDTO) -> AdminKeyResponse:
        rows = await self._db.query('SELECT id FROM "admins" WHERE user_id = :uid', {"uid": dto.actor_id})
        if not rows:
            raise NotFoundError("Admin not found")
        key, now = new_admin_key(), utc_now().replace(microsecond=0)
        await self._db.update("admins", rows[0]["id"], {"key_hash": hash_admin_key(key), "key_created_at": now})
        await audit(self._db, dto.actor_id, "rotate_key", ip=dto.ip)
        return AdminKeyResponse(key=key, created_at=now.isoformat())


# ---------- сводка ----------

class DashboardResponse(BaseModel):
    users_by_role: dict[str, int]
    blocked_users: int
    new_users_7d: int
    new_users_30d: int
    lessons_next_7d: int
    lessons_by_status_30d: dict[str, int]
    pending_requests: int
    blog_posts: int
    boards: int
    quizzes: int
    recent_audit: list[dict]


def _count(rows) -> int:
    return int(rows[0]["n"]) if rows else 0


@register_scenario("admin_dashboard", dto=AdminActorDTO, response=DashboardResponse)
class AdminDashboardScenario(BaseScenario):
    async def execute(self, dto: AdminActorDTO) -> DashboardResponse:
        now = utc_now()
        q = self._db.query
        roles = await q('SELECT r.name, COUNT(u.id) AS n FROM "roles" r LEFT JOIN "users" u ON u.role_id = r.id GROUP BY r.name', {})
        statuses = await q(
            'SELECT COALESCE(status, :d) AS status, COUNT(*) AS n FROM "lessons" '
            'WHERE start_time >= :since GROUP BY COALESCE(status, :d)',
            {"since": now - datetime.timedelta(days=30), "d": "SCHEDULED"},
        )
        audit_rows = await q(
            'SELECT a.id, a.created_at, a.action, a.target, a.ip, u.username FROM "admin_audit" a '
            'LEFT JOIN "users" u ON u.id = a.admin_user_id ORDER BY a.id DESC LIMIT 8', {})
        return DashboardResponse(
            users_by_role={r["name"]: int(r["n"]) for r in roles},
            blocked_users=_count(await q('SELECT COUNT(*) AS n FROM "users" WHERE blocked_at IS NOT NULL', {})),
            new_users_7d=_count(await q('SELECT COUNT(*) AS n FROM "users" WHERE created_at >= :t',
                                        {"t": now - datetime.timedelta(days=7)})),
            new_users_30d=_count(await q('SELECT COUNT(*) AS n FROM "users" WHERE created_at >= :t',
                                         {"t": now - datetime.timedelta(days=30)})),
            lessons_next_7d=_count(await q(
                'SELECT COUNT(*) AS n FROM "lessons" WHERE start_time >= :a AND start_time < :b '
                "AND (status IS NULL OR status IN ('SCHEDULED', 'PENDING'))",
                {"a": now, "b": now + datetime.timedelta(days=7)})),
            lessons_by_status_30d={r["status"]: int(r["n"]) for r in statuses},
            pending_requests=_count(await q('SELECT COUNT(*) AS n FROM "lessons" WHERE status = :s', {"s": "PENDING"})),
            blog_posts=_count(await q('SELECT COUNT(*) AS n FROM "blog_posts"', {})),
            boards=_count(await q('SELECT COUNT(*) AS n FROM "boards"', {})),
            quizzes=_count(await q('SELECT COUNT(*) AS n FROM "quizzes"', {})),
            recent_audit=[_audit_item(r) for r in audit_rows],
        )


# ---------- журнал действий ----------

def _audit_item(row: dict) -> dict:
    created = row.get("created_at")
    return {
        "id": row["id"],
        "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
        "admin": row.get("username"),
        "action": row["action"],
        "target": row.get("target"),
        "details": parse_value(row.get("details"), "dict"),
        "ip": row.get("ip"),
    }


class AuditListDTO(AdminActorDTO):
    action: str | None = Field(default=None, max_length=64)
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class AuditListResponse(BaseModel):
    items: list[dict]
    total: int


@register_scenario("admin_audit_list", dto=AuditListDTO, response=AuditListResponse)
class AdminAuditListScenario(BaseScenario):
    async def execute(self, dto: AuditListDTO) -> AuditListResponse:
        where, params = "", {"lim": dto.limit, "off": dto.offset}
        if dto.action:
            where, params["action"] = "WHERE a.action = :action", dto.action
        rows = await self._db.query(
            'SELECT a.*, u.username FROM "admin_audit" a LEFT JOIN "users" u ON u.id = a.admin_user_id '
            f'{where} ORDER BY a.id DESC LIMIT :lim OFFSET :off', params)
        total = await self._db.query(f'SELECT COUNT(*) AS n FROM "admin_audit" a {where}', params)
        return AuditListResponse(items=[_audit_item(r) for r in rows], total=_count(total))


# ---------- пользователи ----------

class UserActionDTO(AdminActorDTO):
    user_id: int = 0
    reason: str | None = Field(default=None, max_length=500)


class UserActionResponse(BaseModel):
    user_id: int
    ok: bool = True
    # Только для сброса пароля: показывается владельцу один раз.
    temporary_password: str | None = None


async def _target(db, dto: UserActionDTO) -> dict:
    if dto.user_id == dto.actor_id:
        raise ConflictError("You cannot apply this action to yourself")
    user = await db.read("users", dto.user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


@register_scenario("admin_block_user", dto=UserActionDTO, response=UserActionResponse)
class AdminBlockUserScenario(BaseScenario):
    async def execute(self, dto: UserActionDTO) -> UserActionResponse:
        user = await _target(self._db, dto)
        await self._db.update("users", user["id"], {
            "blocked_at": utc_now().replace(microsecond=0),
            "block_reason": (dto.reason or "").strip() or None,
            "refresh_token": None,  # все сеансы закрыты
        })
        blocklist.mark_blocked(user["id"])
        await audit(self._db, dto.actor_id, "block_user", f"user:{user['id']} {user['username']}",
                    {"reason": dto.reason}, dto.ip)
        return UserActionResponse(user_id=user["id"])


@register_scenario("admin_unblock_user", dto=UserActionDTO, response=UserActionResponse)
class AdminUnblockUserScenario(BaseScenario):
    async def execute(self, dto: UserActionDTO) -> UserActionResponse:
        user = await _target(self._db, dto)
        await self._db.update("users", user["id"], {"blocked_at": None, "block_reason": None})
        blocklist.mark_unblocked(user["id"])
        await audit(self._db, dto.actor_id, "unblock_user", f"user:{user['id']} {user['username']}", ip=dto.ip)
        return UserActionResponse(user_id=user["id"])


def _temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(14))


@register_scenario("admin_reset_password", dto=UserActionDTO, response=UserActionResponse)
class AdminResetPasswordScenario(BaseScenario):
    async def execute(self, dto: UserActionDTO) -> UserActionResponse:
        user = await _target(self._db, dto)
        admins = await self._db.query('SELECT id FROM "admins" WHERE user_id = :uid', {"uid": user["id"]})
        if admins:
            raise ConflictError("Administrators sign in with a key, not a password")
        password = _temporary_password()
        await self._db.update("users", user["id"], {
            "password_hash": await hash_password(password),
            "refresh_token": None,
        })
        await audit(self._db, dto.actor_id, "reset_password", f"user:{user['id']} {user['username']}", ip=dto.ip)
        return UserActionResponse(user_id=user["id"], temporary_password=password)


@register_scenario("admin_delete_user", dto=UserActionDTO, response=UserActionResponse)
class AdminDeleteUserScenario(BaseScenario):
    async def execute(self, dto: UserActionDTO) -> UserActionResponse:
        user = await _target(self._db, dto)
        await delete_user_data(self._db, user["id"], user)
        blocklist.mark_unblocked(user["id"])
        await audit(self._db, dto.actor_id, "delete_user", f"user:{user['id']} {user['username']}",
                    {"email": user.get("email"), "full_name": user.get("full_name")}, dto.ip)
        return UserActionResponse(user_id=user["id"])


# ---------- служебное ----------

class CountResponse(BaseModel):
    count: int


@register_scenario("admin_load_blocklist", response=CountResponse)
class AdminLoadBlocklistScenario(BaseScenario):
    async def execute(self, dto=None) -> CountResponse:
        return CountResponse(count=await blocklist.load(self._db))
