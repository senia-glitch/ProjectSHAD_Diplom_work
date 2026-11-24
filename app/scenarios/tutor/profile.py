from typing import Literal
from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO
from app.utils.json_codec import parse_row, parse_int_list, serialize_for_db
from app.utils.clock import utc_now
from app.utils.safe_parse import parse_iso_datetime, to_dt
from app.utils.notifications import format_lesson_time, get_user_name, notify_participants
from app.utils.validation import (
    TIME_OF_DAY_PATTERN,
    TIME_OF_DAY_START_PATTERN,
    time_of_day_value,
    TIMEZONE_OFFSET_MIN,
    TIMEZONE_OFFSET_MAX,
    HOURS_IN_YEAR,
)


def _validate_display_window(settings, new_from, new_to) -> None:
    """Окно сетки: from < to; "24:00" допустимо только как конец."""
    effective_from = new_from if new_from is not None else settings["display_time_from"]
    effective_to = new_to if new_to is not None else settings["display_time_to"]
    from_time = time_of_day_value(effective_from)
    to_time = time_of_day_value(effective_to)
    if from_time >= to_time:
        raise ValidationError("display_time_from must be less than display_time_to")



class TutorGetMyProfileDTO(BaseDTO):
    pass


class TutorUpdateMySettingsDTO(BaseDTO):
    hourly_rate: float | None = Field(default=None, ge=0)
    discount: float | None = Field(default=None, ge=0, le=100)
    timezone_offset: int | None = Field(
        default=None, ge=TIMEZONE_OFFSET_MIN, le=TIMEZONE_OFFSET_MAX
    )
    # Отсутствие с границами (наивный UTC). NONE — снять период.
    absence_status: Literal["VACATION", "SICK", "NONE"] | None = None
    absence_from: str | None = None
    absence_to: str | None = None
    auto_confirm_bookings: bool | None = None
    require_link_consent: bool | None = None
    schedule_type: Literal["INFORMATIVE", "MINIMALISTIC"] | None = None
    display_time_from: str | None = Field(default=None, pattern=TIME_OF_DAY_START_PATTERN)
    display_time_to: str | None = Field(default=None, pattern=TIME_OF_DAY_PATTERN)
    self_booking_mode: Literal["YES", "NO"] | None = None
    self_booking_whitelist: list[int] | None = None
    booking_lead_time_hours: int | None = Field(default=None, ge=0, le=HOURS_IN_YEAR)
    cancellation_lead_time_hours: int | None = Field(default=None, ge=0, le=HOURS_IN_YEAR)
    default_links: list[dict] | None = None


class TutorGetMyProfileResponse(BaseModel):
    tutor_id: int
    hourly_rate: float
    discount: float
    timezone_offset: int
    work_status: str
    schedule_type: str
    display_time_from: str
    display_time_to: str
    self_booking_mode: str
    self_booking_whitelist: list[int] | None
    booking_lead_time_hours: int
    cancellation_lead_time_hours: int
    default_links: list[dict] | None
    auto_confirm_bookings: bool = True
    require_link_consent: bool = True
    absence_status: str | None = None
    absence_from: str | None = None
    absence_to: str | None = None


def effective_work_status(settings: dict, now=None) -> str:
    """Статус работы сейчас: отпуск/болезнь только внутри заданного периода."""
    status = settings.get("absence_status")
    start, end = settings.get("absence_from"), settings.get("absence_to")
    if not status or not start or not end:
        return "WORKING"
    now = now or utc_now()
    return status if to_dt(start) <= now < to_dt(end) else "WORKING"


def _iso(value):
    return to_dt(value).isoformat() if value else None


def profile_payload(s: dict) -> dict:
    return {
        "tutor_id": s["tutor_id"],
        "hourly_rate": s["hourly_rate"],
        "discount": s["discount"],
        "timezone_offset": s["timezone_offset"],
        "work_status": effective_work_status(s),
        "schedule_type": s["schedule_type"],
        "display_time_from": s["display_time_from"],
        "display_time_to": s["display_time_to"],
        "self_booking_mode": s["self_booking_mode"],
        "self_booking_whitelist": s["self_booking_whitelist"],
        "booking_lead_time_hours": s["booking_lead_time_hours"],
        "cancellation_lead_time_hours": s["cancellation_lead_time_hours"],
        "default_links": s["default_links"],
        "auto_confirm_bookings": bool(s.get("auto_confirm_bookings", True)),
        "require_link_consent": bool(s.get("require_link_consent", True)),
        "absence_status": s.get("absence_status"),
        "absence_from": _iso(s.get("absence_from")),
        "absence_to": _iso(s.get("absence_to")),
    }


@register_scenario("tutor_get_my_profile", dto=TutorGetMyProfileDTO, response=TutorGetMyProfileResponse)
@tracked_scenario("tutor_get_my_profile")
class TutorGetMyProfileScenario(BaseScenario):
    async def execute(self, dto: TutorGetMyProfileDTO) -> TutorGetMyProfileResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        settings = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        if not settings:
            raise NotFoundError("Tutor settings not found")
        s = parse_row("tutor_settings", settings[0])
        return TutorGetMyProfileResponse(**profile_payload(s))


class TutorUpdateMySettingsResponse(BaseModel):
    tutor_id: int
    hourly_rate: float
    discount: float
    timezone_offset: int
    work_status: str
    schedule_type: str
    display_time_from: str
    display_time_to: str
    self_booking_mode: str
    self_booking_whitelist: list[int] | None
    booking_lead_time_hours: int
    cancellation_lead_time_hours: int
    default_links: list[dict] | None
    auto_confirm_bookings: bool = True
    require_link_consent: bool = True
    absence_status: str | None = None
    absence_from: str | None = None
    absence_to: str | None = None


@register_scenario("tutor_update_my_settings", dto=TutorUpdateMySettingsDTO, response=TutorUpdateMySettingsResponse)
@tracked_scenario("tutor_update_my_settings")
class TutorUpdateMySettingsScenario(BaseScenario):
    async def execute(self, dto: TutorUpdateMySettingsDTO) -> TutorUpdateMySettingsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        settings = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        if not settings:
            raise NotFoundError("Tutor settings not found")
        settings_id = settings[0]["id"]

        update_fields = {}
        field_map = {
            "hourly_rate": dto.hourly_rate,
            "discount": dto.discount,
            "timezone_offset": dto.timezone_offset,
            "auto_confirm_bookings": dto.auto_confirm_bookings,
            "require_link_consent": dto.require_link_consent,
            "schedule_type": dto.schedule_type,
            "display_time_from": dto.display_time_from,
            "display_time_to": dto.display_time_to,
            "self_booking_mode": dto.self_booking_mode,
            "self_booking_whitelist": dto.self_booking_whitelist,
            "booking_lead_time_hours": dto.booking_lead_time_hours,
            "cancellation_lead_time_hours": dto.cancellation_lead_time_hours,
            "default_links": dto.default_links,
        }
        for key, value in field_map.items():
            if value is not None:
                update_fields[key] = value

        if "display_time_from" in update_fields or "display_time_to" in update_fields:
            _validate_display_window(settings[0], dto.display_time_from, dto.display_time_to)

        absence_changed = False
        if dto.absence_status == "NONE":
            update_fields.update({"absence_status": None, "absence_from": None, "absence_to": None,
                                  "work_status": "WORKING"})
        elif dto.absence_status is not None:
            if not dto.absence_from or not dto.absence_to:
                raise ValidationError("absence_from and absence_to are required")
            start = parse_iso_datetime(dto.absence_from, "absence_from")
            end = parse_iso_datetime(dto.absence_to, "absence_to")
            if start >= end:
                raise ValidationError("absence_from must be less than absence_to")
            if end <= utc_now():
                raise ValidationError("Absence period is already over")
            update_fields.update({"absence_status": dto.absence_status, "absence_from": start,
                                  "absence_to": end, "work_status": "WORKING"})
            absence_changed = True

        if update_fields:
            update_fields = serialize_for_db("tutor_settings", update_fields)
            await self._db.update("tutor_settings", settings_id, update_fields)

        if dto.self_booking_mode is not None or dto.self_booking_whitelist is not None:
            updated_settings = await self._db.query(
                'SELECT self_booking_mode, self_booking_whitelist FROM "tutor_settings" WHERE id = :id',
                {"id": settings_id},
            )
            mode = updated_settings[0]["self_booking_mode"]
            whitelist = parse_int_list(updated_settings[0].get("self_booking_whitelist"))

            configs = await self._db.query(
                'SELECT id, student_id, allow_self_booking FROM "configurations" WHERE tutor_id = :tid',
                {"tid": tutor_id},
            )
            for cfg in configs:
                if mode == "YES":
                    allow = True
                else:
                    allow = cfg["student_id"] in whitelist
                if cfg["allow_self_booking"] != allow:
                    await self._db.update("configurations", cfg["id"], {"allow_self_booking": allow})

        updated = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE id = :id',
            {"id": settings_id},
        )
        u = parse_row("tutor_settings", updated[0])

        if absence_changed:
            await _notify_frozen_lessons(self._db, tutor_id, token.user_id, u)
        return TutorUpdateMySettingsResponse(**profile_payload(u))


async def _notify_frozen_lessons(db, tutor_id: int, tutor_user_id: int, settings: dict) -> None:
    """Ученикам уроков, попавших на отпуск/болезнь: урок заморожен, не отменён."""
    start, end = to_dt(settings["absence_from"]), to_dt(settings["absence_to"])
    lessons = await db.query(
        'SELECT id, start_time FROM "lessons" WHERE tutor_id = :tid AND start_time < :pe AND end_time > :ps '
        "AND (status IS NULL OR status IN ('SCHEDULED', 'PENDING'))",
        {"tid": tutor_id, "ps": start, "pe": end},
    )
    if not lessons:
        return
    name = await get_user_name(db, tutor_user_id)
    label = "в отпуске" if settings["absence_status"] == "VACATION" else "болеет"
    for lesson in lessons:
        await notify_participants(
            db, lesson["id"], "lesson_frozen",
            f"Репетитор {name} {label} с {format_lesson_time(start)} по {format_lesson_time(end)}: "
            f"урок {format_lesson_time(lesson['start_time'])} заморожен",
        )
