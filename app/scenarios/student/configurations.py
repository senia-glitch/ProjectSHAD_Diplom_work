from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.json_codec import serialize_for_db, parse_row
from app.utils.configurations import (
    validate_not_same_user,
    validate_configuration_not_exists,
    build_configuration_create_data,
    resolve_allow_self_booking,
)
from app.utils.notifications import notify_user, get_user_name, get_tutor_user_id

from core.dto import BaseDTO


class StudentGetMyConfigurationsDTO(BaseDTO):
    pass


class ConfigurationItem(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int
    hourly_rate: float
    allow_self_booking: bool
    link_visibility_enabled: bool = False
    link_lead_time_minutes: int = 0


class StudentGetMyConfigurationsResponse(BaseModel):
    configurations: list[ConfigurationItem]


class StudentGetConfigurationDTO(BaseDTO):
    config_id: int


class StudentGetConfigurationResponse(BaseModel):
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
    default_links: list[dict] | None
    allow_unpaid_lesson: bool
    # student_notes — внутренняя заметка репетитора, ученику не отдаётся.
    link_visibility_enabled: bool
    link_lead_time_minutes: int
    tutor_user_id: int | None = None
    tutor_username: str | None = None
    tutor_full_name: str | None = None
    tutor_work_status: str | None = None


class StudentCreateConfigurationDTO(BaseDTO):
    tutor_user_id: int


class StudentCreateConfigurationResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int


class StudentCreateConfigurationByCodeDTO(BaseDTO):
    personal_number: str


class StudentCreateConfigurationByCodeResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int


class StudentDeleteConfigurationDTO(BaseDTO):
    config_id: int


class StudentDeleteConfigurationResponse(BaseModel):
    ok: bool


@register_scenario("student_get_my_configurations")
@tracked_scenario("student_get_my_configurations")
class StudentGetMyConfigurationsScenario(BaseScenario):
    async def execute(self, dto: StudentGetMyConfigurationsDTO) -> StudentGetMyConfigurationsResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE student_id = :sid ORDER BY id LIMIT :lim OFFSET :off',
            {"sid": student_id, "lim": dto.limit, "off": dto.offset},
        )

        configs = [
            ConfigurationItem(
                config_id=r["id"],
                student_id=r["student_id"],
                tutor_id=r["tutor_id"],
                hourly_rate=r["hourly_rate"],
                allow_self_booking=r["allow_self_booking"],
                link_visibility_enabled=r["link_visibility_enabled"],
                link_lead_time_minutes=r["link_lead_time_minutes"],
            )
            for r in rows
        ]

        return StudentGetMyConfigurationsResponse(configurations=configs)


@register_scenario("student_get_configuration")
@tracked_scenario("student_get_configuration")
class StudentGetConfigurationScenario(BaseScenario):
    async def execute(self, dto: StudentGetConfigurationDTO) -> StudentGetConfigurationResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            'SELECT * FROM "configurations" WHERE id = :cid',
            {"cid": dto.config_id},
        )
        if not rows:
            raise NotFoundError("Configuration not found")

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")

        if rows[0]["student_id"] != students[0]["id"]:
            raise NotFoundError("Configuration not found")

        r = parse_row("configurations", rows[0])

        tutor_user_id = None
        tutor_username = None
        tutor_full_name = None
        tutor_work_status = None

        tutor_rows = await self._db.query(
            'SELECT id, user_id FROM "tutors" WHERE id = :tid',
            {"tid": r["tutor_id"]},
        )
        if tutor_rows:
            tutor_user_id = tutor_rows[0]["user_id"]
            user_rows = await self._db.query(
                'SELECT username, full_name FROM "users" WHERE id = :uid',
                {"uid": tutor_user_id},
            )
            if user_rows:
                tutor_username = user_rows[0]["username"]
                tutor_full_name = user_rows[0]["full_name"]

            settings_rows = await self._db.query(
                'SELECT work_status FROM "tutor_settings" WHERE tutor_id = :tid',
                {"tid": r["tutor_id"]},
            )
            if settings_rows:
                tutor_work_status = settings_rows[0]["work_status"]

        return StudentGetConfigurationResponse(
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
            link_visibility_enabled=r["link_visibility_enabled"],
            link_lead_time_minutes=r["link_lead_time_minutes"],
            tutor_user_id=tutor_user_id,
            tutor_username=tutor_username,
            tutor_full_name=tutor_full_name,
            tutor_work_status=tutor_work_status,
        )


@register_scenario("student_create_configuration")
@tracked_scenario("student_create_configuration")
class StudentCreateConfigurationScenario(BaseScenario):
    async def execute(self, dto: StudentCreateConfigurationDTO) -> StudentCreateConfigurationResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        validate_not_same_user(token.user_id, dto.tutor_user_id)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": dto.tutor_user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

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
            if "uq_student_tutor" in str(e) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(f"Configuration for student {student_id} and tutor {tutor_id} already exists")
            raise

        student_name = await get_user_name(self._db, token.user_id)
        await notify_user(
            self._db, dto.tutor_user_id, "link_created",
            f"Ученик {student_name} привязался к вам",
        )

        return StudentCreateConfigurationResponse(
            config_id=config["id"],
            student_id=student_id,
            tutor_id=tutor_id,
        )


@register_scenario("student_create_configuration_by_code")
@tracked_scenario("student_create_configuration_by_code")
class StudentCreateConfigurationByCodeScenario(BaseScenario):
    async def execute(self, dto: StudentCreateConfigurationByCodeDTO) -> StudentCreateConfigurationByCodeResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        user_rows = await self._db.query(
            'SELECT id FROM "users" WHERE personal_number = :pn',
            {"pn": dto.personal_number},
        )
        if not user_rows:
            raise NotFoundError("User with this personal number not found")
        target_user_id = user_rows[0]["id"]

        validate_not_same_user(token.user_id, target_user_id)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": target_user_id},
        )
        if not tutors:
            raise NotFoundError("Target user is not a tutor")
        tutor_id = tutors[0]["id"]

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
            if "uq_student_tutor" in str(e) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(f"Configuration for student {student_id} and tutor {tutor_id} already exists")
            raise

        student_name = await get_user_name(self._db, token.user_id)
        await notify_user(
            self._db, target_user_id, "link_created",
            f"Ученик {student_name} привязался к вам",
        )

        return StudentCreateConfigurationByCodeResponse(
            config_id=config["id"],
            student_id=student_id,
            tutor_id=tutor_id,
        )


@register_scenario("student_delete_configuration")
@tracked_scenario("student_delete_configuration")
class StudentDeleteConfigurationScenario(BaseScenario):
    async def execute(self, dto: StudentDeleteConfigurationDTO) -> StudentDeleteConfigurationResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            'SELECT id, student_id, tutor_id FROM "configurations" WHERE id = :cid',
            {"cid": dto.config_id},
        )
        if not rows:
            raise NotFoundError("Configuration not found")

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")

        if rows[0]["student_id"] != students[0]["id"]:
            raise NotFoundError("Configuration not found")

        await self._db.delete("configurations", dto.config_id)

        tutor_user_id = await get_tutor_user_id(self._db, rows[0]["tutor_id"])
        if tutor_user_id is not None:
            student_name = await get_user_name(self._db, token.user_id)
            await notify_user(
                self._db, tutor_user_id, "link_deleted",
                f"Ученик {student_name} отвязался от вас",
            )

        return StudentDeleteConfigurationResponse(ok=True)


