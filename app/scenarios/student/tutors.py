import datetime
from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.json_codec import parse_int_list
from app.utils.participants import is_cancelled_row
from app.utils.safe_parse import parse_iso_date, parse_iso_datetime
from app.utils.schedule import get_available_slots, merge_lessons, subtract_blocks
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

        tutor_settings = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        if not tutor_settings or tutor_settings[0]["work_status"] != "WORKING":
            raise ValidationError("Tutor is not working")

        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid',
            {"sid": student_id, "tid": tutor_id},
        )
        if not configs:
            raise NotFoundError("Configuration not found")
        config = configs[0]
        if not config["allow_self_booking"]:
            raise ForbiddenError("Self-booking is not allowed by configuration")

        tutor_settings_rows = await self._db.query(
            'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        if tutor_settings_rows:
            ts = tutor_settings_rows[0]
            mode = ts.get("self_booking_mode", "YES")
            if mode == "NO":
                whitelist = parse_int_list(ts.get("self_booking_whitelist"))
                if student_id not in whitelist:
                    raise ForbiddenError("Self-booking is not available for you")

        lead_hours = config["booking_lead_time_hours"]
        now = datetime.datetime.now()
        earliest = now + datetime.timedelta(hours=lead_hours)

        date_from = parse_iso_date(dto.date_from, "date_from")
        date_to = parse_iso_date(dto.date_to, "date_to")
        date_start = parse_iso_datetime(f"{dto.date_from}T00:00:00", "date_from")
        date_end = parse_iso_datetime(f"{dto.date_to}T23:59:59", "date_to")

        # Один запрос броней репетитора вместо N запросов по дням.
        tutor_bookings = await self._db.query(
            'SELECT * FROM "bookings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        bookings_by_weekday: dict[str, list] = {}
        for b in tutor_bookings:
            bookings_by_weekday.setdefault(b.get("weekday"), []).append(b)

        all_available_slots = []
        current_date = date_from
        while current_date <= date_to:
            WEEKDAYS = {0: "MONDAY", 1: "TUESDAY", 2: "WEDNESDAY", 3: "THURSDAY", 4: "FRIDAY", 5: "SATURDAY", 6: "SUNDAY"}
            weekday_name = WEEKDAYS[current_date.weekday()]
            day_bookings = bookings_by_weekday.get(weekday_name, [])
            # Нет подходящих броней — день закрыт. Подстановки окна
            # отображения здесь нет и быть не должно: display_time_* —
            # только визуальный диапазон сетки, не право на запись.
            day_slots = get_available_slots(day_bookings, student_id, "00:00", "24:00")
            next_day = current_date + datetime.timedelta(days=1)
            for slot in day_slots:
                # "24:00:00" — полночь следующих суток, иначе ISO-парсер упадёт.
                slot_start = f"{current_date.isoformat()}T{slot['start']}" if slot['start'] != "24:00:00" else f"{next_day.isoformat()}T00:00:00"
                slot_end = f"{current_date.isoformat()}T{slot['end']}" if slot['end'] != "24:00:00" else f"{next_day.isoformat()}T00:00:00"
                all_available_slots.append({"start": slot_start, "end": slot_end})
            current_date += datetime.timedelta(days=1)

        participations = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE student_id = :sid',
            {"sid": student_id},
        )
        # Один диапазонный запрос уроков ученика вместо N точечных.
        range_lessons = await self._db.query(
            'SELECT id, start_time, end_time, status FROM "lessons" WHERE start_time <= :de AND end_time >= :ds',
            {"ds": date_start, "de": date_end},
        )
        lessons_by_id = {l["id"]: l for l in range_lessons}
        student_lessons_in_range = []
        for p in participations:
            if is_cancelled_row(p):
                continue
            lesson = lessons_by_id.get(p["lesson_id"])
            if lesson is None:
                continue
            if (lesson.get("status") or "SCHEDULED") == "CANCELLED":
                continue
            lesson_start_date = _get_date(lesson["start_time"])
            lesson_end_date = _get_date(lesson["end_time"])
            # Занятость: урок занимает каждый день диапазона, который он
            # пересекает (полуоткрытые интервалы — как в student_create_lesson).
            if lesson_end_date >= date_from and lesson_start_date <= date_to:
                student_lessons_in_range.append({
                    "start_time": _to_iso(lesson["start_time"]),
                    "end_time": _to_iso(lesson["end_time"]),
                })

        # Урок, начавшийся раньше, но кончающийся внутри диапазона, тоже занимает.
        tutor_lessons_raw = await self._db.query(
            'SELECT start_time, end_time, status FROM "lessons" WHERE tutor_id = :tid AND start_time <= :de AND end_time >= :ds',
            {"tid": tutor_id, "ds": date_start, "de": date_end},
        )
        tutor_lessons_in_range = [
            {"start_time": _to_iso(l["start_time"]), "end_time": _to_iso(l["end_time"])}
            for l in tutor_lessons_raw
            if (l.get("status") or "SCHEDULED") != "CANCELLED"
        ]

        merged_blocks = merge_lessons(student_lessons_in_range, tutor_lessons_in_range)
        free_slots = subtract_blocks(all_available_slots, merged_blocks)

        result = []
        for slot in free_slots:
            slot_start = parse_iso_datetime(slot["start"], "slot.start")
            if slot_start >= earliest:
                result.append(LessonSlot(start=slot["start"], end=slot["end"]))

        return StudentGetAvailableSlotsResponse(slots=result)
