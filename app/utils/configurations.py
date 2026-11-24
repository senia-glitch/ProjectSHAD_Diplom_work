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


LINK_ACTIVE = "ACTIVE"
LINK_PENDING = "PENDING"


def initial_link_state(require_consent: bool, requested_by: str, now) -> dict:
    """Состояние новой связи: при включённом согласии второй стороны — заявка."""
    if require_consent:
        return {"status": LINK_PENDING, "requested_by": requested_by, "requested_at": now}
    return {"status": LINK_ACTIVE, "requested_by": requested_by, "requested_at": now}


def validate_link_receiver(config: dict, role: str) -> None:
    """Принять/отклонить заявку на связь может только вторая сторона."""
    if (config.get("status") or LINK_ACTIVE) != LINK_PENDING:
        raise ValidationError("Link is not awaiting confirmation")
    if config.get("requested_by") == role:
        raise ValidationError("Only the other side can answer this link request")
