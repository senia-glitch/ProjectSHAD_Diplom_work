"""Заблокированные пользователи — в памяти процесса.

Токен доступа — JWT без обращения к БД, живёт до 30 минут. Чтобы блокировка действовала
сразу, `authenticate` сверяется с этим множеством. Приложение работает одним процессом
(FAT_WORKERS=1): множество загружается из БД при старте и меняется сценариями админки.
"""
_blocked: set[int] = set()


def is_blocked(user_id: int | None) -> bool:
    return user_id is not None and user_id in _blocked


def mark_blocked(user_id: int) -> None:
    _blocked.add(int(user_id))


def mark_unblocked(user_id: int) -> None:
    _blocked.discard(int(user_id))


def replace(user_ids) -> None:
    _blocked.clear()
    _blocked.update(int(x) for x in user_ids)


async def load(db) -> int:
    rows = await db.query('SELECT id FROM "users" WHERE blocked_at IS NOT NULL', {})
    replace(r["id"] for r in rows)
    return len(_blocked)
