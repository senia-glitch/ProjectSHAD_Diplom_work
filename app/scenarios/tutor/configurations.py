from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.core.exceptions import ForbiddenError
from core import ConflictError
from app.utils.json_codec import serialize_for_db, parse_row
from app.utils.db_errors import is_unique_violation
from app.utils.validation import HOURS_IN_YEAR
from app.utils.configurations import (
    validate_not_same_user,
    validate_configuration_not_exists,
    build_configuration_create_data,
    build_configuration_update_data,
    resolve_allow_self_booking,
    sync_allow_self_booking_into_whitelist,
)
from app.utils.notifications import notify_user, get_user_name, get_student_user_id

from core.dto import BaseDTO


class TutorGetMyConfigurationsDTO(BaseDTO):
    pass


class ConfigurationItem(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int
    hourly_rate: float
    allow_self_booking: bool


class TutorGetMyConfigurationsResponse(BaseModel):
    configurations: list[ConfigurationItem]


class TutorGetConfigurationDTO(BaseDTO):
    config_id: int


class TutorGetConfigurationResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int
    hourly_rate: float
    discount: float
    slot_step_minutes: int
    allow_self_booking: bool
    booking_lead_time_hours: int
    cancellation_lead_time_hours: int
    notifications_enabled: bool
    notification_lead_time_hours: int
    default_links: list[dict] | None = None
    allow_unpaid_lesson: bool
    student_notes: str | None
    link_visibility_enabled: bool
    link_lead_time_minutes: int


class TutorCreateConfigurationDTO(BaseDTO):
    student_user_id: int


class TutorCreateConfigurationResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int


class TutorCreateConfigurationByCodeDTO(BaseDTO):
    personal_number: str


class TutorCreateConfigurationByCodeResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int


class TutorUpdateConfigurationDTO(BaseDTO):
    config_id: int | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    discount: float | None = Field(default=None, ge=0, le=100)
    slot_step_minutes: int | None = Field(default=None, ge=1, le=1440)
    allow_self_booking: bool | None = None
    booking_lead_time_hours: int | None = Field(default=None, ge=0, le=HOURS_IN_YEAR)
    cancellation_lead_time_hours: int | None = Field(default=None, ge=0, le=HOURS_IN_YEAR)
    notifications_enabled: bool | None = None
    notification_lead_time_hours: int | None = Field(default=None, ge=0, le=HOURS_IN_YEAR)
    default_links: list[dict] | None = None
    allow_unpaid_lesson: bool | None = None
    student_notes: str | None = Field(default=None, max_length=5000)
    link_visibility_enabled: bool | None = None
    link_lead_time_minutes: int | None = Field(default=None, ge=0, le=15)


class TutorUpdateConfigurationResponse(BaseModel):
    config_id: int


class TutorDeleteConfigurationDTO(BaseDTO):
    config_id: int


class TutorDeleteConfigurationResponse(BaseModel):
    ok: bool


class TutorResetConfigurationDTO(BaseDTO):
    config_id: int | None = None


class TutorResetConfigurationResponse(BaseModel):
    config_id: int


@register_scenario("tutor_get_my_configurations", dto=TutorGetMyConfigurationsDTO, response=TutorGetMyConfigurationsResponse)
@tracked_scenario("tutor_get_my_configurations")
class TutorGetMyConfigurationsScenario(BaseScenario):
    async def execute(self, dto: TutorGetMyConfigurationsDTO) -> TutorGetMyConfigurationsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE tutor_id = :tid ORDER BY id LIMIT :lim OFFSET :off',
            {"tid": tutor_id, "lim": dto.limit, "off": dto.offset},
        )

        configs = [
            ConfigurationItem(
                config_id=r["id"],
                student_id=r["student_id"],
                tutor_id=r["tutor_id"],
                hourly_rate=r["hourly_rate"],
                allow_self_booking=r["allow_self_booking"],
            )
            for r in rows
        ]

        return TutorGetMyConfigurationsResponse(configurations=configs)


@register_scenario("tutor_get_configuration", dto=TutorGetConfigurationDTO, response=TutorGetConfigurationResponse)
@tracked_scenario("tutor_get_configuration")
class TutorGetConfigurationScenario(BaseScenario):
    async def execute(self, dto: TutorGetConfigurationDTO) -> TutorGetConfigurationResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE id = :cid AND tutor_id = :tid',
            {"cid": dto.config_id, "tid": tutor_id},
        )
        if not rows:
            raise NotFoundError("Configuration not found")

        r = parse_row("configurations", rows[0])
        return TutorGetConfigurationResponse(
            config_id=r["id"],
            student_id=r["student_id"],
            tutor_id=r["tutor_id"],
            hourly_rate=r["hourly_rate"],
            discount=r["discount"],
            slot_step_minutes=r["slot_step_minutes"],
            allow_self_booking=r["allow_self_booking"],
            booking_lead_time_hours=r["booking_lead_time_hours"],
            cancellation_lead_time_hours=r["cancellation_lead_time_hours"],
            notifications_enabled=r["notifications_enabled"],
            notification_lead_time_hours=r["notification_lead_time_hours"],
            default_links=r.get("default_links"),
            allow_unpaid_lesson=r["allow_unpaid_lesson"],
            student_notes=r.get("student_notes"),
            link_visibility_enabled=r["link_visibility_enabled"],
            link_lead_time_minutes=r["link_lead_time_minutes"],
        )


@register_scenario("tutor_create_configuration", dto=TutorCreateConfigurationDTO, response=TutorCreateConfigurationResponse)
@tracked_scenario("tutor_create_configuration")
class TutorCreateConfigurationScenario(BaseScenario):
    async def execute(self, dto: TutorCreateConfigurationDTO) -> TutorCreateConfigurationResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": dto.student_user_id},
        )
        if not students:
            raise NotFoundError("Student not found")
        student_id = students[0]["id"]

        validate_not_same_user(token.user_id, dto.student_user_id)

        existing = await self._db.query(
            'SELECT id FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid',
            {"sid": student_id, "tid": tutor_id},
        )
        validate_configuration_not_exists(student_id, tutor_id, bool(existing))

        tutor_settings_rows = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )

        data = build_configuration_create_data(student_id, tutor_id)
        data["slot_step_minutes"] = 60
        data["link_visibility_enabled"] = False
        data["link_lead_time_minutes"] = 0
        if tutor_settings_rows:
            ts = parse_row("tutor_settings", tutor_settings_rows[0])
            for key in ("hourly_rate", "discount", "booking_lead_time_hours",
                        "cancellation_lead_time_hours"):
                data[key] = ts[key]
            if ts.get("default_links") is not None:
                data["default_links"] = ts.get("default_links")
            data["allow_self_booking"] = resolve_allow_self_booking(
                ts.get("self_booking_mode"), ts.get("self_booking_whitelist"), student_id
            )

        data = serialize_for_db("configurations", data)
        try:
            config = await self._db.create("configurations", data)
        except Exception as e:
            if is_unique_violation(e):
                raise ConflictError(f"Configuration for student {student_id} and tutor {tutor_id} already exists")
            raise

        tutor_name = await get_user_name(self._db, token.user_id)
        await notify_user(
            self._db, dto.student_user_id, "link_created",
            f"Репетитор {tutor_name} привязал вас",
        )

        return TutorCreateConfigurationResponse(
            config_id=config["id"],
            student_id=student_id,
            tutor_id=tutor_id,
        )


@register_scenario("tutor_create_configuration_by_code", dto=TutorCreateConfigurationByCodeDTO, response=TutorCreateConfigurationByCodeResponse)
@tracked_scenario("tutor_create_configuration_by_code")
class TutorCreateConfigurationByCodeScenario(BaseScenario):
    async def execute(self, dto: TutorCreateConfigurationByCodeDTO) -> TutorCreateConfigurationByCodeResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        user_rows = await self._db.query(
            'SELECT id FROM "users" WHERE personal_number = :pn',
            {"pn": dto.personal_number},
        )
        if not user_rows:
            raise NotFoundError("User with this personal number not found")
        target_user_id = user_rows[0]["id"]

        validate_not_same_user(target_user_id, token.user_id)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": target_user_id},
        )
        if not students:
            raise NotFoundError("Target user is not a student")
        student_id = students[0]["id"]

        existing = await self._db.query(
            'SELECT id FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid',
            {"sid": student_id, "tid": tutor_id},
        )
        validate_configuration_not_exists(student_id, tutor_id, bool(existing))

        tutor_settings_rows = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )

        data = build_configuration_create_data(student_id, tutor_id)
        data["slot_step_minutes"] = 60
        data["link_visibility_enabled"] = False
        data["link_lead_time_minutes"] = 0
        if tutor_settings_rows:
            ts = parse_row("tutor_settings", tutor_settings_rows[0])
            for key in ("hourly_rate", "discount", "booking_lead_time_hours",
                        "cancellation_lead_time_hours"):
                data[key] = ts[key]
            if ts.get("default_links") is not None:
                data["default_links"] = ts.get("default_links")
            data["allow_self_booking"] = resolve_allow_self_booking(
                ts.get("self_booking_mode"), ts.get("self_booking_whitelist"), student_id
            )

        data = serialize_for_db("configurations", data)
        try:
            config = await self._db.create("configurations", data)
        except Exception as e:
            if is_unique_violation(e):
                raise ConflictError(f"Configuration for student {student_id} and tutor {tutor_id} already exists")
            raise

        tutor_name = await get_user_name(self._db, token.user_id)
        await notify_user(
            self._db, target_user_id, "link_created",
            f"Репетитор {tutor_name} привязал вас",
        )

        return TutorCreateConfigurationByCodeResponse(
            config_id=config["id"],
            student_id=student_id,
            tutor_id=tutor_id,
        )


@register_scenario("tutor_update_configuration", dto=TutorUpdateConfigurationDTO, response=TutorUpdateConfigurationResponse)
@tracked_scenario("tutor_update_configuration")
class TutorUpdateConfigurationScenario(BaseScenario):
    async def execute(self, dto: TutorUpdateConfigurationDTO) -> TutorUpdateConfigurationResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE id = :cid',
            {"cid": dto.config_id},
        )
        if not rows:
            raise NotFoundError("Configuration not found")

        if rows[0]["tutor_id"] != tutor_id:
            raise ForbiddenError("You do not own this configuration")

        if dto.slot_step_minutes is not None and dto.slot_step_minutes <= 0:
            raise ValidationError("slot_step_minutes must be greater than 0")

        if dto.link_lead_time_minutes is not None and not 0 <= dto.link_lead_time_minutes <= 15:
            raise ValidationError("link_lead_time_minutes must be between 0 and 15")

        update_data = build_configuration_update_data({
            k: v for k, v in dto.model_dump().items()
            if k not in ("access_token", "limit", "offset", "config_id") and v is not None
        })

        if update_data:
            update_data = serialize_for_db("configurations", update_data)
            await self._db.update("configurations", dto.config_id, update_data)

        if "allow_self_booking" in update_data:
            # Двусторонняя связь с настройками: пер-ученический флаг
            # правит whitelist, чтобы страница «Ученики» всегда показывала
            # эффективное значение (enforcement: флаг И (YES ИЛИ whitelist)).
            settings_rows = await self._db.query(
                'SELECT id, self_booking_whitelist FROM "tutor_settings" WHERE tutor_id = :tid',
                {"tid": tutor_id},
            )
            if settings_rows:
                synced = sync_allow_self_booking_into_whitelist(
                    settings_rows[0].get("self_booking_whitelist"),
                    rows[0]["student_id"],
                    bool(update_data["allow_self_booking"]),
                )
                await self._db.update(
                    "tutor_settings",
                    settings_rows[0]["id"],
                    serialize_for_db("tutor_settings", {"self_booking_whitelist": synced}),
                )

        return TutorUpdateConfigurationResponse(config_id=dto.config_id)


@register_scenario("tutor_delete_configuration", dto=TutorDeleteConfigurationDTO, response=TutorDeleteConfigurationResponse)
@tracked_scenario("tutor_delete_configuration")
class TutorDeleteConfigurationScenario(BaseScenario):
    async def execute(self, dto: TutorDeleteConfigurationDTO) -> TutorDeleteConfigurationResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE id = :cid',
            {"cid": dto.config_id},
        )
        if not rows:
            raise NotFoundError("Configuration not found")

        if rows[0]["tutor_id"] != tutor_id:
            raise ForbiddenError("You do not own this configuration")

        await self._db.delete("configurations", dto.config_id)

        student_user_id = await get_student_user_id(self._db, rows[0]["student_id"])
        if student_user_id is not None:
            tutor_name = await get_user_name(self._db, token.user_id)
            await notify_user(
                self._db, student_user_id, "link_deleted",
                f"Репетитор {tutor_name} отвязал вас",
            )

        return TutorDeleteConfigurationResponse(ok=True)


@register_scenario("tutor_reset_configuration", dto=TutorResetConfigurationDTO, response=TutorResetConfigurationResponse)
@tracked_scenario("tutor_reset_configuration")
class TutorResetConfigurationScenario(BaseScenario):
    async def execute(self, dto: TutorResetConfigurationDTO) -> TutorResetConfigurationResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE id = :cid',
            {"cid": dto.config_id},
        )
        if not rows:
            raise NotFoundError("Configuration not found")

        if rows[0]["tutor_id"] != tutor_id:
            raise ForbiddenError("You do not own this configuration")

        settings_rows = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        if not settings_rows:
            raise NotFoundError("Tutor settings not found")
        ts = parse_row("tutor_settings", settings_rows[0])

        # Приведение к значениям для новых учеников (без самозаписи:
        # флаг и whitelist не трогаем). Остальные поля конфигурации
        # (уведомления, заметки, неоплаченные) — не дефолты, не трогаем.
        reset_data = {
            key: ts[key]
            for key in ("hourly_rate", "discount", "booking_lead_time_hours",
                        "cancellation_lead_time_hours")
        }
        reset_data["default_links"] = ts.get("default_links")
        reset_data["slot_step_minutes"] = 60
        reset_data["link_visibility_enabled"] = False
        reset_data["link_lead_time_minutes"] = 0
        reset_data = serialize_for_db("configurations", reset_data)
        await self._db.update("configurations", dto.config_id, reset_data)

        return TutorResetConfigurationResponse(config_id=dto.config_id)
