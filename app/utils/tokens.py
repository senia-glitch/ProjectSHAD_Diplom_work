"""Refresh-токены: хэширование и хранение списка активных сессий.

users.refresh_token хранит JSON-список хэшей (до MAX_REFRESH_SESSIONS):
каждая вкладка/устройство имеет свою сессию. Один хэш (строка без JSON)
— запись старого формата, читается как список из одного элемента.
"""
import asyncio
import hashlib
import json

MAX_REFRESH_SESSIONS = 5

# Сериализация между "ждущими" ротациями одного пользователя: read-modify-write
# списка сессий не должен отдавать два деланных результата по одному снимку.
_refresh_locks: dict[int, asyncio.Lock] = {}
_refresh_locks_guard = asyncio.Lock()


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def parse_refresh_hashes(value) -> list[str]:
    """Список хэшей активных refresh-сессий из сохранённого значения."""
    if not value:
        return []
    text = str(value).strip()
    if text.startswith("["):
        try:
            data = json.loads(text)
        except ValueError:
            return []
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str) and x]
        return []
    return [text]


def format_refresh_hashes(hashes: list[str]) -> str | None:
    """Сериализация списка хэшей; пустой список → None (сессий нет)."""
    fresh = [str(x) for x in hashes if str(x)]
    if not fresh:
        return None
    return json.dumps(fresh[:MAX_REFRESH_SESSIONS], separators=(",", ":"))


def create_refresh_store(current, new_hash: str) -> str:
    """Добавляет новую сессию в начало списка (старые выдавливаются)."""
    hashes = parse_refresh_hashes(current)
    return format_refresh_hashes([new_hash, *[h for h in hashes if h != new_hash]])


def rotate_refresh_store(current: str, old_hash: str, new_hash: str) -> list[str]:
    """Ротация: вместо old_hash появляется new_hash в голове списка."""
    hashes = parse_refresh_hashes(current).copy()
    if old_hash in hashes:
        hashes.remove(old_hash)
    return [new_hash, *hashes][:MAX_REFRESH_SESSIONS]


def revoke_refresh_session(current, old_hash: str) -> str | None:
    """Удаляет одну сессию (logout этой вкладки); остальные остаются."""
    rest = [h for h in parse_refresh_hashes(current) if h != old_hash]
    return format_refresh_hashes(rest)


async def auth_user_lock(user_id: int) -> asyncio.Lock:
    """Лок аутентифик-операций пользователя (login/logout/refresh)."""
    async with _refresh_locks_guard:
        lock = _refresh_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            _refresh_locks[user_id] = lock
        return lock
