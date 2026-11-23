"""Чистая бизнес-логика участников уроков. Без IO-зависимостей."""

import datetime
import math
from core import ValidationError, ConflictError
from app.core.exceptions import ForbiddenError
from app.utils.lessons import TERMINAL_LESSON_STATUSES


def validate_lesson_not_ended(
    lesson_end: datetime.datetime,
    now: datetime.datetime | None = None,
) -> None:
    """Вступить можно пока урок не кончился (ONGOING разрешён)."""
    if now is None:
        now = datetime.datetime.now()
    if lesson_end < now:
        raise ValidationError("Cannot join ended lesson")


def validate_lesson_not_terminal(status: str | None) -> None:
    """Выход/снятие — только из нетерминального урока: историю не переписываем."""
    if status in TERMINAL_LESSON_STATUSES:
        raise ValidationError(f"Cannot leave lesson in status {status}")


def validate_cancellation_deadline(
    now: datetime.datetime,
    lesson_start: datetime.datetime,
    lead_hours: int,
    student_id: int,
) -> None:
    deadline = lesson_start - datetime.timedelta(hours=lead_hours)
    if now > deadline:
        raise ValidationError(
            f"Cancellation deadline passed for student {student_id} "
            f"({lead_hours}h before lesson)"
        )


def validate_not_already_participant(existing_participants: list) -> None:
    if existing_participants:
        raise ConflictError("Student is already a participant")


def validate_is_lesson_owner(
    lesson_tutor_id: int, caller_tutor_id: int
) -> None:
    if lesson_tutor_id != caller_tutor_id:
        raise ForbiddenError("You can only manage your own lessons")


PRICE_SNAPSHOT_CURRENCY = "RUB"


def cancellation_of(settings: dict | None) -> dict | None:
    """Отмена записи из participant_settings. Нет ключа — активна."""
    if not isinstance(settings, dict):
        return None
    cancelled = settings.get("cancelled")
    return cancelled if isinstance(cancelled, dict) else None


def is_cancelled_row(row: dict) -> bool:
    """Строка lesson_participants (сырая из БД) отменена или нет."""
    from app.utils.json_codec import parse_value
    settings = parse_value(row.get("participant_settings"), "dict")
    return cancellation_of(settings) is not None


def build_cancellation(by: str, now: datetime.datetime | None = None) -> dict:
    """Пометка отмены записи. by: 'student' | 'tutor'."""
    if now is None:
        now = datetime.datetime.now()
    return {"by": by, "at": now.isoformat()}


def validate_not_cancelled(row: dict) -> None:
    if is_cancelled_row(row):
        raise ValidationError("Participant record is cancelled")


def final_price_per_hour(hourly_rate: float, discount: float) -> int:
    """Итоговая цена часа со скидкой. Зеркалит frontend pricing.finalPrice.

    Фронтенд использует Math.round (половинные вверх), поэтому здесь то же
    правило для неотрицательных значений — вместо banker's round().
    """
    value = hourly_rate * (1 - discount / 100)
    return math.floor(value + 0.5)


def build_price_snapshot(
    hourly_rate: float,
    discount: float,
    config_id: int,
    now: datetime.datetime | None = None,
) -> dict:
    """Снапшот цены связи на момент добавления ученика в урок.

    Кладётся в participant_settings одной записью вместе с созданием
    участника. Дальнейшая смена тарифа в конфигурации историю не трогает:
    выручка считается по замороженной цене.
    """
    if now is None:
        now = datetime.datetime.now().replace(microsecond=0)
    return {
        "price_snapshot": {
            "hourly_rate": hourly_rate,
            "discount": discount,
            "final_per_hour": final_price_per_hour(hourly_rate, discount),
            "currency": PRICE_SNAPSHOT_CURRENCY,
            "config_id": config_id,
            "snapshot_at": now.isoformat(),
        }
    }
