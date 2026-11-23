# Безопасный парсинг ISO дат/времени.
# Правило: голый datetime.fromisoformat/time.fromisoformat/date.fromisoformat
# ЗАПРЕЩЁН в сценариях — он бросает ValueError -> 500.
# Всегда используйте parse_* ниже: они бросают ValidationError (422/400),
# которую фронт умеет показывать.

import datetime

from core import ValidationError


def parse_iso_datetime(value: str, field: str = "datetime") -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid {field}: expected ISO datetime, got {value!r}")
    if dt.tzinfo is not None:
        # Правило проекта: сервер работает только в своём локальном времени.
        # Aware-вход конвертируем в локальную зону сервера и убираем tzinfo,
        # а не отбрасываем смещение (иначе сдвигаем момент времени).
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def parse_iso_date(value: str, field: str = "date") -> datetime.date:
    if value is None or value == "":
        raise ValidationError(f"Invalid {field}: expected ISO date YYYY-MM-DD, got {value!r}")
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid {field}: expected ISO date YYYY-MM-DD, got {value!r}")


def parse_iso_time(value: str, field: str = "time") -> datetime.time:
    try:
        return datetime.time.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid {field}: expected ISO time HH:MM[:SS], got {value!r}")


def to_dt(value) -> datetime.datetime:
    """Универсальное приведение значения из БД/DTO к datetime. Не для валидации ввода."""
    if isinstance(value, datetime.datetime):
        return value.astimezone().replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str):
        return parse_iso_datetime(value.replace(" ", "T"))
    return value
