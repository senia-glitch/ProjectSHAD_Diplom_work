"""Общие константы и ограничения валидации DTO.

Значения синхронизированы с frontend/src/logic/constants/*.
"""

from typing import Annotated

from pydantic import BeforeValidator, Field

# Время суток "HH:MM" (00:00–23:59) либо "24:00" как полночь конца суток.
# "24:00" допустимо ТОЛЬКО для display_time_to: начало окна — исключительно
# HH:MM в пределах суток (см. TIME_OF_DAY_START_PATTERN).
TIME_OF_DAY_PATTERN = r"^(?:([01]\d|2[0-3]):[0-5]\d|24:00)$"
TIME_OF_DAY_START_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


def time_of_day_value(value: str):
    """Строка окна отображения → datetime.time ("24:00" → 23:59:59.999999)."""
    import datetime

    if value in ("24:00", "24:00:00"):
        return datetime.time.max
    return datetime.time.fromisoformat(value)

# Логин/email (простая проверка формата вместо полной RFC-валидации).
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# Диапазоны числовых тарифов/лимитов.
TIMEZONE_OFFSET_MIN = -12
TIMEZONE_OFFSET_MAX = 14
HOURS_IN_YEAR = 8760
MINUTES_IN_WEEK = 10080

WORK_STATUSES = ("WORKING", "SICK", "VACATION")
SCHEDULE_VIEWS = ("INFORMATIVE", "MINIMALISTIC")
SELF_BOOKING_MODES = ("YES", "NO")
STUDENT_STATUSES = ("ACTIVE", "INACTIVE")

# bcrypt принимает не более 72 БАЙТ (не символов). Более длинный пароль
# роняет hash/check с ValueError -> 500, поэтому режем на границе DTO.
BCRYPT_MAX_BYTES = 72


def _check_password_bytes(v):
    if isinstance(v, str) and len(v.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"password must be at most {BCRYPT_MAX_BYTES} bytes")
    return v


# Новый пароль (регистрация, смена): политика длины + лимит bcrypt.
PasswordStr = Annotated[
    str, BeforeValidator(_check_password_bytes), Field(min_length=8, max_length=72)
]
# Ввод пароля при логине: только лимит bcrypt (политику не подсказываем).
PasswordInputStr = Annotated[
    str, BeforeValidator(_check_password_bytes), Field(max_length=72)
]
