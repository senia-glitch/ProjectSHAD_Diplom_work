"""Чистая бизнес-логика конфигураций. Без IO-зависимостей."""

from core import ValidationError, ConflictError
from app.utils.json_codec import parse_int_list


def validate_not_same_user(student_user_id: int, tutor_user_id: int) -> None:
    if student_user_id == tutor_user_id:
        raise ValidationError("Student and tutor cannot be the same user")


def validate_configuration_not_exists(
    student_id: int, tutor_id: int, exists: bool
) -> None:
    if exists:
        raise ConflictError(
            f"Configuration for student {student_id} and tutor {tutor_id} already exists"
        )


def build_configuration_create_data(
    student_profile_id: int, tutor_profile_id: int
) -> dict:
    return {
        "student_id": student_profile_id,
        "tutor_id": tutor_profile_id,
    }


def build_configuration_update_data(dto_fields: dict) -> dict:
    result = {}
    for k, v in dto_fields.items():
        if v is not None:
            result[k] = v
    return result


def resolve_allow_self_booking(mode: str | None, whitelist, student_id: int) -> bool:
    """Эффективное значение флага при создании связи.

    Зеркалит пропагацию из TutorUpdateMySettingsScenario:
    режим YES открывает всем, иначе решает whitelist.
    """
    if (mode or "YES") == "YES":
        return True
    return int(student_id) in parse_int_list(whitelist)


def sync_allow_self_booking_into_whitelist(whitelist, student_id: int, allow: bool) -> list[int]:
    """Возвращает whitelist, согласованный с пер-ученическим флагом.

    Вызывается при правке configurations.allow_self_booking репетитором,
    чтобы флаг на странице «Ученики» всегда совпадал с реальностью
    (enforcement: флаг И (режим YES ИЛИ whitelist)).
    """
    ids = parse_int_list(whitelist)
    sid = int(student_id)
    if allow and sid not in ids:
        ids.append(sid)
    if not allow and sid in ids:
        ids.remove(sid)
    return ids
