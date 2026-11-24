from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.participants import is_cancelled_row
from app.utils.safe_parse import parse_range, to_dt
from app.utils.lessons import NON_BLOCKING_LESSON_STATUSES
from core.dto import BaseDTO


class TutorListStudentsDTO(BaseDTO):
    pass


class TutorListStudentItem(BaseModel):
    student_id: int
    user_id: int
    full_name: str


class TutorListStudentsResponse(BaseModel):
    students: list[TutorListStudentItem]


@register_scenario("tutor_list_students", dto=TutorListStudentsDTO, response=TutorListStudentsResponse)
@tracked_scenario("tutor_list_students")
class TutorListStudentsScenario(BaseScenario):
    async def execute(self, dto: TutorListStudentsDTO) -> TutorListStudentsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        rows = await self._db.query(
            '''SELECT s.id AS student_id, s.user_id, u.full_name
               FROM "configurations" c
               JOIN "students" s ON s.id = c.student_id
               JOIN "users" u ON u.id = s.user_id
               WHERE c.tutor_id = :tid AND c.status = :active
               ORDER BY u.full_name''',
            {"tid": tutor_id, "active": "ACTIVE"},
        )

        return TutorListStudentsResponse(
            students=[TutorListStudentItem(**r) for r in rows]
        )


class TutorGetStudentBusySlotsDTO(BaseDTO):
    student_user_id: int
    date_from: str = Field(..., description="Start date in YYYY-MM-DD format")
    date_to: str = Field(..., description="End date in YYYY-MM-DD format")


class BusySlot(BaseModel):
    start: str
    end: str


class TutorGetStudentBusySlotsResponse(BaseModel):
    busy_slots: list[BusySlot]


def _to_iso(value) -> str:
    if isinstance(value, str):
        return value.replace(" ", "T")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@register_scenario("tutor_get_student_busy_slots", dto=TutorGetStudentBusySlotsDTO, response=TutorGetStudentBusySlotsResponse)
@tracked_scenario("tutor_get_student_busy_slots")
class TutorGetStudentBusySlotsScenario(BaseScenario):
    async def execute(self, dto: TutorGetStudentBusySlotsDTO) -> TutorGetStudentBusySlotsResponse:
        token = extract_token_info(dto.access_token)

        range_start, range_end = parse_range(dto.date_from, dto.date_to)

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

        configs = await self._db.query(
            'SELECT id FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid AND status = :active',
            {"sid": student_id, "tid": tutor_id, "active": "ACTIVE"},
        )
        if not configs:
            raise NotFoundError("No configuration found for this student-tutor pair")

        participations = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE student_id = :sid',
            {"sid": student_id},
        )

        busy_slots = []
        for p in participations:
            # Отменённая запись время не занимает.
            if is_cancelled_row(p):
                continue
            lesson_rows = await self._db.query(
                'SELECT * FROM "lessons" WHERE id = :lid',
                {"lid": p["lesson_id"]},
            )
            if not lesson_rows:
                continue
            lesson = lesson_rows[0]
            # Отменённый/отклонённый урок и заявка время не занимают.
            if (lesson.get("status") or "SCHEDULED") in NON_BLOCKING_LESSON_STATUSES:
                continue
            start = lesson["start_time"]
            end = lesson["end_time"]
            # Полуоткрытые интервалы: урок пересекает UTC-диапазон периода.
            if to_dt(start) < range_end and to_dt(end) > range_start:
                busy_slots.append(BusySlot(
                    start=_to_iso(start),
                    end=_to_iso(end),
                ))

        return TutorGetStudentBusySlotsResponse(busy_slots=busy_slots)
