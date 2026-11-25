# Единый кодек сериализации/десериализации JSON-полей.
#
# Проблема, которую решает модуль:
# - в БД (через event-infra -> asyncpg, raw UPDATE ... $N) JSON-колонки
#   ожидают JSON-СТРОКУ, а не Python list/dict. Голый list/dict роняет
#   запрос: `invalid input for query argument $9: []`.
# - при чтении драйвер может вернуть list/dict (SQLAlchemy JSON),
#   str (дважды закодированный JSON) или None. Код сценариев должен
#   всегда работать с Python-объектами, а не угадывать тип.
#
# Правила (строго):
# 1. DTO/бизнес-логика работают ТОЛЬКО с Python-объектами (list/dict/None).
# 2. Перед ЛЮБЫМ self._db.create/update JSON-поля прогоняются через
#    serialize_for_db(table, data). Никогда не делать ручной json.dumps.
# 3. Сразу после ЛЮБОГО self._db.query/read, вернувшего JSON-колонки,
#    прогонять строку через parse_row/parse_rows. Никогда не делать
#    ручной json.loads вне этого модуля.
# 4. None = "не задано". []/{} = "пусто, но задано". Не путать.
# 5. Проверки вида `x in whitelist` делать ТОЛЬКО после parse_int_list(),
#    иначе при whitelist: str проверка работает как поиск подстроки.

import json as _json
from typing import Any

# Реестр: таблица -> {поле: ожидаемый тип}.
# Ожидаемый тип нужен только для восстановления при битых данных.
JSON_FIELDS: dict[str, dict[str, str]] = {
    "tutor_settings": {
        "self_booking_whitelist": "list",
        "default_links": "list",
    },
    "configurations": {
        "default_links": "list",
    },
    "bookings": {
        "access_targets": "list",
        "booking_metadata": "dict",
    },
    "lessons": {
        "lesson_settings": "dict",
        "lesson_links": "list",
        "lesson_metadata": "dict",
        "status_history": "list",
    },
    "lesson_participants": {
        "participant_settings": "dict",
        "participant_metadata": "dict",
    },
    "notifications": {
        "payload": "dict",
    },
    "admin_audit": {
        "details": "dict",
    },
}


def _default_for(expect: str) -> Any:
    return [] if expect == "list" else ({} if expect == "dict" else None)


def dumps_value(value: Any) -> Any:
    """Python-объект -> значение для БД. None/str проходят как есть."""
    if value is None or isinstance(value, str):
        return value
    return _json.dumps(value, ensure_ascii=False)


def parse_value(value: Any, expect: str = "any") -> Any:
    """Значение из БД -> Python-объект. Никогда не бросает исключение."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode("utf-8")
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return _json.loads(s)
        except Exception:
            # Битый JSON: возвращаем дефолт по ожидаемому типу,
            # чтобы проверки `in` и Pydantic не падали.
            if expect in ("list", "dict"):
                return _default_for(expect)
            return None
    return value


def parse_int_list(value: Any) -> list[int]:
    """Строго list[int] для whitelist/access_targets. Всегда возвращает list."""
    parsed = parse_value(value, "list")
    if not isinstance(parsed, list):
        return []
    result: list[int] = []
    for item in parsed:
        try:
            result.append(int(item))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    return result


def serialize_for_db(table: str, data: dict) -> dict:
    """Сериализовать JSON-поля таблицы перед create/update. Возвращает новый dict."""
    fields = JSON_FIELDS.get(table, {})
    if not fields:
        return dict(data)
    result = dict(data)
    for key in fields:
        if key in result:
            result[key] = dumps_value(result[key])
    return result


def parse_row(table: str, row: dict) -> dict:
    """Десериализовать JSON-поля одной строки из БД. Возвращает новый dict."""
    fields = JSON_FIELDS.get(table, {})
    if not fields:
        return dict(row)
    result = dict(row)
    for key, expect in fields.items():
        if key in result:
            result[key] = parse_value(result[key], expect)
    return result


def parse_rows(table: str, rows: list[dict]) -> list[dict]:
    """Десериализовать JSON-поля списка строк из БД."""
    return [parse_row(table, r) for r in rows]
