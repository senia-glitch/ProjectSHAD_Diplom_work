from typing import Literal
from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO
from app.utils.validation import (
    TIME_OF_DAY_PATTERN,
    TIME_OF_DAY_START_PATTERN,
    time_of_day_value,
    TIMEZONE_OFFSET_MIN,
    TIMEZONE_OFFSET_MAX,
)


def _validate_display_window(settings, new_from, new_to) -> None:
    """Окно сетки: from < to; "24:00" допустимо только как конец."""
    effective_from = new_from if new_from is not None else settings["display_time_from"]
    effective_to = new_to if new_to is not None else settings["display_time_to"]
    from_time = time_of_day_value(effective_from)
    to_time = time_of_day_value(effective_to)
    if from_time >= to_time:
        raise ValidationError("display_time_from must be less than display_time_to")


class StudentGetMyProfileDTO(BaseDTO):
    pass


class StudentGetMyProfileResponse(BaseModel):
    student_id: int
    status: str
    timezone_offset: int
    schedule_view: str
    display_time_from: str
    display_time_to: str


@register_scenario("student_get_my_profile", dto=StudentGetMyProfileDTO, response=StudentGetMyProfileResponse)
@tracked_scenario("student_get_my_profile")
class StudentGetMyProfileScenario(BaseScenario):
    async def execute(self, dto: StudentGetMyProfileDTO) -> StudentGetMyProfileResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")

        student_id = students[0]["id"]
        settings = await self._db.query(
            'SELECT * FROM "student_settings" WHERE student_id = :sid',
            {"sid": student_id},
        )
        if not settings:
            raise NotFoundError("Student settings not found")

        s = settings[0]
        return StudentGetMyProfileResponse(
            student_id=student_id,
            status=s["status"],
            timezone_offset=s["timezone_offset"],
            schedule_view=s["schedule_view"],
            display_time_from=s["display_time_from"],
            display_time_to=s["display_time_to"],
        )


class StudentUpdateMySettingsDTO(BaseDTO):
    status: Literal["ACTIVE", "INACTIVE"] | None = Field(default=None)
    timezone_offset: int | None = Field(
        default=None, ge=TIMEZONE_OFFSET_MIN, le=TIMEZONE_OFFSET_MAX
    )
    schedule_view: Literal["INFORMATIVE", "MINIMALISTIC"] | None = Field(default=None)
    display_time_from: str | None = Field(default=None, pattern=TIME_OF_DAY_START_PATTERN)
    display_time_to: str | None = Field(default=None, pattern=TIME_OF_DAY_PATTERN)


class StudentUpdateMySettingsResponse(BaseModel):
    student_id: int
    status: str
    timezone_offset: int
    schedule_view: str
    display_time_from: str
    display_time_to: str


@register_scenario("student_update_my_settings", dto=StudentUpdateMySettingsDTO, response=StudentUpdateMySettingsResponse)
@tracked_scenario("student_update_my_settings")
class StudentUpdateMySettingsScenario(BaseScenario):
    async def execute(self, dto: StudentUpdateMySettingsDTO) -> StudentUpdateMySettingsResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")

        student_id = students[0]["id"]
        settings = await self._db.query(
            'SELECT * FROM "student_settings" WHERE student_id = :sid',
            {"sid": student_id},
        )
        if not settings:
            raise NotFoundError("Student settings not found")

        settings_id = settings[0]["id"]
        update_data = {}
        if dto.status is not None:
            update_data["status"] = dto.status
        if dto.timezone_offset is not None:
            update_data["timezone_offset"] = dto.timezone_offset
        if dto.schedule_view is not None:
            update_data["schedule_view"] = dto.schedule_view
        if dto.display_time_from is not None:
            update_data["display_time_from"] = dto.display_time_from
        if dto.display_time_to is not None:
            update_data["display_time_to"] = dto.display_time_to
        if "display_time_from" in update_data or "display_time_to" in update_data:
            _validate_display_window(settings[0], dto.display_time_from, dto.display_time_to)

        if update_data:
            await self._db.update("student_settings", settings_id, update_data)

        updated = await self._db.query(
            'SELECT * FROM "student_settings" WHERE id = :id',
            {"id": settings_id},
        )
        u = updated[0]

        return StudentUpdateMySettingsResponse(
            student_id=student_id,
            status=u["status"],
            timezone_offset=u["timezone_offset"],
            schedule_view=u["schedule_view"],
            display_time_from=u["display_time_from"],
            display_time_to=u["display_time_to"],
        )
