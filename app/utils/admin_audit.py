"""Журнал действий администратора и ключ входа владельца."""
import hashlib
import secrets

from app.utils.clock import utc_now
from app.utils.json_codec import serialize_for_db

KEY_PREFIX = "shad_admin_"
KEY_BYTES = 32  # 256 бит энтропии: перебор ключа невозможен


def new_admin_key() -> str:
    """Новый ключ владельца (показывается один раз; в БД — только хэш)."""
    return KEY_PREFIX + secrets.token_urlsafe(KEY_BYTES)


def hash_admin_key(key: str) -> str:
    # Ключ — случайная строка высокой энтропии, поэтому достаточно SHA-256 (как у refresh-токенов).
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


async def audit(db, admin_user_id: int | None, action: str, target: str | None = None,
                details: dict | None = None, ip: str | None = None) -> None:
    """Запись в журнал действий. Ошибка журнала не должна молча терять действие — пробрасывается."""
    await db.create("admin_audit", serialize_for_db("admin_audit", {
        "admin_user_id": admin_user_id,
        "action": action,
        "target": (target or "")[:255] or None,
        "details": details or None,
        "ip": (ip or "")[:64] or None,
        "created_at": utc_now(),
    }))
