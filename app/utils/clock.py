"""Единые часы приложения: всё время в системе — наивный UTC.

Сервер хранит, сравнивает и считает время только в UTC. Личный часовой пояс
пользователя (смещение в часах из его настроек) — лишь способ показать время:
клиент переводит его на границе API, сервер — в текстах уведомлений.
"""
import datetime

UTC = datetime.timezone.utc


def utc_now() -> datetime.datetime:
    """Текущий момент как наивный UTC (формат хранения в БД)."""
    return datetime.datetime.now(UTC).replace(tzinfo=None)


def to_utc_naive(value: datetime.datetime) -> datetime.datetime:
    """Aware → наивный UTC; наивное значение уже считается UTC."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def to_local(value: datetime.datetime, offset_hours: int | float | None) -> datetime.datetime:
    """Наивный UTC → наивное «стенное» время пользователя со смещением offset_hours."""
    return value + datetime.timedelta(hours=offset_hours or 0)


def from_local(value: datetime.datetime, offset_hours: int | float | None) -> datetime.datetime:
    """Наивное «стенное» время пользователя → наивный UTC."""
    return value - datetime.timedelta(hours=offset_hours or 0)
