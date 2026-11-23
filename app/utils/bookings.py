"""Чистая бизнес-логика броней. Без IO-зависимостей."""

import datetime
from core import ValidationError, ConflictError


WEEKDAY_NAMES = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)


def validate_weekday(weekday: str) -> None:
    if weekday not in WEEKDAY_NAMES:
        raise ValidationError(
            f"Invalid weekday: {weekday}. Must be one of: {', '.join(WEEKDAY_NAMES)}"
        )


def validate_booking_times(
    start_time: datetime.time,
    end_time: datetime.time,
) -> None:
    if start_time >= end_time:
        raise ValidationError("start_time must be less than end_time")


def check_booking_overlap(overlapping_bookings: list) -> None:
    if overlapping_bookings:
        raise ConflictError("Booking overlaps with an existing one")


def build_booking_update_data(dto_fields: dict) -> dict:
    result = {}
    for k, v in dto_fields.items():
        if v is not None:
            result[k] = v
    return result
