from typing import Literal
from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO
from app.utils.json_codec import parse_row, parse_int_list, serialize_for_db
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
    work_status: Literal["WORKING", "SICK", "VACATION"] | None = None
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


@register_scenario("tutor_get_my_profile")
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

        return TutorGetMyProfileResponse(
            tutor_id=s["tutor_id"],
            hourly_rate=s["hourly_rate"],
            discount=s["discount"],
            timezone_offset=s["timezone_offset"],
            work_status=s["work_status"],
            schedule_type=s["schedule_type"],
            display_time_from=s["display_time_from"],
            display_time_to=s["display_time_to"],
            self_booking_mode=s["self_booking_mode"],
            self_booking_whitelist=s["self_booking_whitelist"],
            booking_lead_time_hours=s["booking_lead_time_hours"],
            cancellation_lead_time_hours=s["cancellation_lead_time_hours"],
            default_links=s["default_links"],
        )


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


@register_scenario("tutor_update_my_settings")
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
            'SELECT id, display_time_from, display_time_to FROM "tutor_settings" WHERE tutor_id = :tid',
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
            "work_status": dto.work_status,
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

        return TutorUpdateMySettingsResponse(
            tutor_id=u["tutor_id"],
            hourly_rate=u["hourly_rate"],
            discount=u["discount"],
            timezone_offset=u["timezone_offset"],
            work_status=u["work_status"],
            schedule_type=u["schedule_type"],
            display_time_from=u["display_time_from"],
            display_time_to=u["display_time_to"],
            self_booking_mode=u["self_booking_mode"],
            self_booking_whitelist=u["self_booking_whitelist"],
            booking_lead_time_hours=u["booking_lead_time_hours"],
            cancellation_lead_time_hours=u["cancellation_lead_time_hours"],
            default_links=u["default_links"],
        )
