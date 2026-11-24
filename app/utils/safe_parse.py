# Безопасный парсинг ISO дат/времени.
# Правило: голый datetime.fromisoformat/time.fromisoformat/date.fromisoformat
# ЗАПРЕЩЁН в сценариях — он бросает ValueError -> 500.
# Всегда используйте parse_* ниже: они бросают ValidationError (422/400),
# которую фронт умеет показывать.

import datetime

from core import ValidationError
from app.utils.clock import to_utc_naive


def parse_iso_datetime(value: str, field: str = "datetime") -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid {field}: expected ISO datetime, got {value!r}")
    if dt.tzinfo is not None:
        # Правило проекта: сервер работает только в UTC (наивное хранение).
        # Aware-вход переводим в UTC и убираем tzinfo,
        # а не отбрасываем смещение (иначе сдвигаем момент времени).
        dt = to_utc_naive(dt)
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
        return to_utc_naive(value)
    if isinstance(value, str):
        return parse_iso_datetime(value.replace(" ", "T"))
    return value


def parse_range(date_from: str, date_to: str) -> tuple[datetime.datetime, datetime.datetime]:
    """Полуоткрытый UTC-диапазон [start, end) из параметров периода.

    Клиент передаёт границы своего периода уже в UTC как дату-время
    (местная неделя пользователя не совпадает с сутками UTC). Голая дата
    по-прежнему допустима: это сутки UTC целиком, конец — включительно.
    """
    def bound(value, field, end):
        text = str(value or "")
        if "T" in text or " " in text:
            return parse_iso_datetime(text.replace(" ", "T"), field)
        day = parse_iso_date(text, field)
        moment = datetime.datetime.combine(day, datetime.time.min)
        return moment + datetime.timedelta(days=1) if end else moment

    start = bound(date_from, "date_from", False)
    end = bound(date_to, "date_to", True)
    if start > end:
        raise ValidationError("date_from must be less than or equal to date_to")
    return start, end
