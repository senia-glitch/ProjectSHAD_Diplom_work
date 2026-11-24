from app.utils.clock import utc_now
import datetime
from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.json_codec import parse_int_list
from app.utils.safe_parse import parse_iso_datetime, parse_range
from app.scenarios.student.availability import free_windows
from core.dto import BaseDTO
from app.core.exceptions import ForbiddenError


class StudentGetAvailableSlotsDTO(BaseDTO):
    tutor_user_id: int
    date_from: str
    date_to: str


class LessonSlot(BaseModel):
    start: str
    end: str


class StudentGetAvailableSlotsResponse(BaseModel):
    slots: list[LessonSlot]


def _get_date(value) -> datetime.date:
    if isinstance(value, str):
        return parse_iso_date(value, "date")
    if hasattr(value, "date"):
        return value.date()
    return parse_iso_date(str(value), "date")


def align_up(window_start: datetime.datetime, moment: datetime.datetime, step_minutes: int) -> datetime.datetime:
    """Первое начало по шагу от начала окна, не раньше moment (шаги считает и клиент от начала окна)."""
    step = max(1, step_minutes)
    minutes = (moment - window_start).total_seconds() / 60
    steps = -(-minutes // step)  # округление вверх
    return window_start + datetime.timedelta(minutes=steps * step)


def _to_iso(value) -> str:
    if isinstance(value, str):
        return value.replace(" ", "T")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@register_scenario("student_get_available_slots", dto=StudentGetAvailableSlotsDTO, response=StudentGetAvailableSlotsResponse)
@tracked_scenario("student_get_available_slots")
class StudentGetAvailableSlotsScenario(BaseScenario):
    async def execute(self, dto: StudentGetAvailableSlotsDTO) -> StudentGetAvailableSlotsResponse:
        token = extract_token_info(dto.access_token)
        student_user_id = token.user_id

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": student_user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        student_settings = await self._db.query(
            'SELECT * FROM "student_settings" WHERE student_id = :sid',
            {"sid": student_id},
        )
        if not student_settings or student_settings[0]["status"] != "ACTIVE":
            raise ValidationError("Student is not active")

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": dto.tutor_user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        tutor_settings_rows = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        ts = tutor_settings_rows[0] if tutor_settings_rows else {}

        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid AND status = :active',
            {"sid": student_id, "tid": tutor_id, "active": "ACTIVE"},
        )
        if not configs:
            raise NotFoundError("Configuration not found")
        config = configs[0]
        if not config["allow_self_booking"]:
            raise ForbiddenError("Self-booking is not allowed by configuration")
        if ts.get("self_booking_mode", "YES") == "NO":
            if student_id not in parse_int_list(ts.get("self_booking_whitelist")):
                raise ForbiddenError("Self-booking is not available for you")

        range_start, range_end = parse_range(dto.date_from, dto.date_to)
        windows = await free_windows(
            self._db, tutor_id=tutor_id, student_id=student_id, tutor_settings=ts,
            start=range_start, end=range_end,
        )

        # Окно, пересекающее границу lead time, не выбрасывается целиком:
        # доступна его часть с первого разрешённого начала по шагу от начала окна.
        earliest = utc_now() + datetime.timedelta(hours=config["booking_lead_time_hours"])
        step = int(config.get("slot_step_minutes") or 60)
        result = []
        for slot in windows:
            slot_start = parse_iso_datetime(slot["start"], "slot.start")
            slot_end = parse_iso_datetime(slot["end"], "slot.end")
            if slot_start < earliest:
                slot_start = align_up(slot_start, earliest, step)
            if slot_start < slot_end:
                result.append(LessonSlot(start=slot_start.isoformat(), end=slot_end.isoformat()))

        return StudentGetAvailableSlotsResponse(slots=result)
