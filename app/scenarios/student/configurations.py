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
from app.utils.configurations import initial_link_state, validate_link_receiver
from app.utils.clock import utc_now
from app.utils.safe_parse import to_dt
from app.scenarios.tutor.profile import effective_work_status, profile_payload


async def _notify_link(db, tutor_user_id: int, student_name: str, pending: bool) -> None:
    if pending:
        await notify_user(
            db, tutor_user_id, "link_requested",
            f"Ученик {student_name} просит добавить его в ваши ученики — ответьте на странице «Ученики»",
        )
    else:
        await notify_user(db, tutor_user_id, "link_created", f"Ученик {student_name} привязался к вам")

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
    # Имя репетитора для списка ученика; поля аддитивные и необязательные.
    tutor_username: str | None = None
    tutor_full_name: str | None = None
    # ACTIVE или PENDING (ждёт согласия), кто запросил связь.
    status: str = "ACTIVE"
    requested_by: str | None = None


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
    # Отпуск/болезнь репетитора с границами — видны ученику (наивный UTC).
    tutor_absence: dict | None = None
    status: str = "ACTIVE"
    requested_by: str | None = None


class StudentCreateConfigurationDTO(BaseDTO):
    tutor_user_id: int


class StudentCreateConfigurationResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int
    status: str = "ACTIVE"


class StudentCreateConfigurationByCodeDTO(BaseDTO):
    personal_number: str


class StudentCreateConfigurationByCodeResponse(BaseModel):
    config_id: int
    student_id: int
    tutor_id: int
    status: str = "ACTIVE"


class StudentDeleteConfigurationDTO(BaseDTO):
    config_id: int


class StudentDeleteConfigurationResponse(BaseModel):
    ok: bool


@register_scenario("student_get_my_configurations", dto=StudentGetMyConfigurationsDTO, response=StudentGetMyConfigurationsResponse)
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
            'SELECT c.*, u.username AS tutor_username, u.full_name AS tutor_full_name '
            'FROM "configurations" c '
            'LEFT JOIN "tutors" t ON t.id = c.tutor_id '
            'LEFT JOIN "users" u ON u.id = t.user_id '
            'WHERE c.student_id = :sid ORDER BY c.id LIMIT :lim OFFSET :off',
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
                tutor_username=r.get("tutor_username"),
                tutor_full_name=r.get("tutor_full_name"),
                status=r.get("status") or "ACTIVE",
                requested_by=r.get("requested_by"),
            )
            for r in rows
        ]

        return StudentGetMyConfigurationsResponse(configurations=configs)


@register_scenario("student_get_configuration", dto=StudentGetConfigurationDTO, response=StudentGetConfigurationResponse)
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
        tutor_absence = None

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
                'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
                {"tid": r["tutor_id"]},
            )
            if settings_rows:
                tutor_work_status = effective_work_status(settings_rows[0])
                absence = profile_payload(parse_row("tutor_settings", settings_rows[0]))
                if absence["absence_status"] and absence["absence_to"] and to_dt(absence["absence_to"]) > utc_now():
                    tutor_absence = {k: absence[f"absence_{k}"] for k in ("status", "from", "to")}

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
            tutor_absence=tutor_absence,
            status=r.get("status") or "ACTIVE",
            requested_by=r.get("requested_by"),
        )


@register_scenario("student_create_configuration", dto=StudentCreateConfigurationDTO, response=StudentCreateConfigurationResponse)
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
            data["auto_confirm_bookings"] = bool(ts.get("auto_confirm_bookings", True))
        require_consent = bool(tutor_settings_rows and tutor_settings_rows[0].get("require_link_consent", True))
        data.update(initial_link_state(require_consent, "student", utc_now()))

        data = serialize_for_db("configurations", data)
        try:
            config = await self._db.create("configurations", data)
        except Exception as e:
            if "uq_student_tutor" in str(e) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(f"Configuration for student {student_id} and tutor {tutor_id} already exists")
            raise

        student_name = await get_user_name(self._db, token.user_id)
        await _notify_link(self._db, dto.tutor_user_id, student_name, require_consent)

        return StudentCreateConfigurationResponse(
            config_id=config["id"],
            student_id=student_id,
            tutor_id=tutor_id,
            status=config.get("status") or "ACTIVE",
        )


@register_scenario("student_create_configuration_by_code", dto=StudentCreateConfigurationByCodeDTO, response=StudentCreateConfigurationByCodeResponse)
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
            data["auto_confirm_bookings"] = bool(ts.get("auto_confirm_bookings", True))
        require_consent = bool(tutor_settings_rows and tutor_settings_rows[0].get("require_link_consent", True))
        data.update(initial_link_state(require_consent, "student", utc_now()))

        data = serialize_for_db("configurations", data)
        try:
            config = await self._db.create("configurations", data)
        except Exception as e:
            if "uq_student_tutor" in str(e) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(f"Configuration for student {student_id} and tutor {tutor_id} already exists")
            raise

        student_name = await get_user_name(self._db, token.user_id)
        await _notify_link(self._db, target_user_id, student_name, require_consent)

        return StudentCreateConfigurationByCodeResponse(
            config_id=config["id"],
            student_id=student_id,
            tutor_id=tutor_id,
            status=config.get("status") or "ACTIVE",
        )


@register_scenario("student_delete_configuration", dto=StudentDeleteConfigurationDTO, response=StudentDeleteConfigurationResponse)
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




class StudentAnswerLinkDTO(BaseDTO):
    config_id: int


class StudentAnswerLinkResponse(BaseModel):
    config_id: int
    status: str


async def _own_link(db, user_id: int, config_id: int) -> dict:
    students = await db.query('SELECT id FROM "students" WHERE user_id = :uid', {"uid": user_id})
    rows = await db.query('SELECT * FROM "configurations" WHERE id = :cid', {"cid": config_id})
    if not students or not rows or rows[0]["student_id"] != students[0]["id"]:
        raise NotFoundError("Configuration not found")
    validate_link_receiver(rows[0], "student")
    return rows[0]


@register_scenario("student_accept_configuration", dto=StudentAnswerLinkDTO, response=StudentAnswerLinkResponse)
@tracked_scenario("student_accept_configuration")
class StudentAcceptConfigurationScenario(BaseScenario):
    async def execute(self, dto: StudentAnswerLinkDTO) -> StudentAnswerLinkResponse:
        token = extract_token_info(dto.access_token)
        config = await _own_link(self._db, token.user_id, dto.config_id)
        await self._db.update("configurations", config["id"], {"status": "ACTIVE"})
        tutor_user_id = await get_tutor_user_id(self._db, config["tutor_id"])
        if tutor_user_id is not None:
            name = await get_user_name(self._db, token.user_id)
            await notify_user(self._db, tutor_user_id, "link_accepted", f"Ученик {name} принял вашу заявку на связь")
        return StudentAnswerLinkResponse(config_id=config["id"], status="ACTIVE")


@register_scenario("student_decline_configuration", dto=StudentAnswerLinkDTO, response=StudentAnswerLinkResponse)
@tracked_scenario("student_decline_configuration")
class StudentDeclineConfigurationScenario(BaseScenario):
    async def execute(self, dto: StudentAnswerLinkDTO) -> StudentAnswerLinkResponse:
        token = extract_token_info(dto.access_token)
        config = await _own_link(self._db, token.user_id, dto.config_id)
        await self._db.delete("configurations", config["id"])
        tutor_user_id = await get_tutor_user_id(self._db, config["tutor_id"])
        if tutor_user_id is not None:
            name = await get_user_name(self._db, token.user_id)
            await notify_user(self._db, tutor_user_id, "link_declined", f"Ученик {name} отклонил заявку на связь")
        return StudentAnswerLinkResponse(config_id=config["id"], status="DECLINED")
