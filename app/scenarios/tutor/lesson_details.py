import datetime
from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO

from app.utils.json_codec import parse_row
from app.utils.safe_parse import parse_iso_date, to_dt
from app.utils.lessons import resolve_lesson_status
from app.utils.participants import final_price_per_hour, cancellation_of
from app.utils.statistics import amount_for_line

# Детализация уроков за период: информацией делятся хронология
# и подробная выгрузка. Жёсткий лимит — защита от сверхвыборки.


class TutorLessonDetailsDTO(BaseDTO):
    date_from: str
    date_to: str
    student_ids: str | None = None


class LessonDetailStudent(BaseModel):
    student_id: int
    student_user_id: int = 0
    student_name: str
    amount: int
    estimated: bool
    paid: bool = False


class LessonDetailRow(BaseModel):
    lesson_id: int
    date: str
    start: str
    end: str
    minutes: int
    is_group: bool
    status: str
    descriptions: str | None = None
    links: list[dict] = []
    students: list[LessonDetailStudent] = []
    total: int


class TutorLessonDetailsResponse(BaseModel):
    lessons: list[LessonDetailRow]
    # Отмены записей по инициаторам за период (сами записи скрыты).
    cancelled_by_student: int = 0
    cancelled_by_tutor: int = 0


def _parse_student_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        raise ValidationError("Invalid student_ids: expected comma-separated integers")


@register_scenario("tutor_lesson_details")
@tracked_scenario("tutor_lesson_details")
class TutorLessonDetailsScenario(BaseScenario):
    async def execute(self, dto: TutorLessonDetailsDTO) -> TutorLessonDetailsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        date_from = parse_iso_date(dto.date_from, "date_from")
        date_to = parse_iso_date(dto.date_to, "date_to")
        if date_from > date_to:
            raise ValidationError("date_from must not be greater than date_to")
        if (date_to - date_from).days > 366:
            raise ValidationError("Date range must not exceed 366 days")
        wanted_students = set(_parse_student_ids(dto.student_ids))

        range_start = datetime.datetime.combine(date_from, datetime.time.min)
        range_end = datetime.datetime.combine(
            date_to + datetime.timedelta(days=1), datetime.time.min
        )

        lessons = await self._db.query(
            'SELECT * FROM "lessons" WHERE tutor_id = :tid '
            'AND start_time >= :from AND start_time < :to '
            'ORDER BY start_time LIMIT 5000',
            {"tid": tutor_id, "from": range_start, "to": range_end},
        )

        participations = await self._db.query(
            'SELECT lp.lesson_id, lp.student_id, lp.participant_settings, u.full_name, s.user_id '
            'FROM "lesson_participants" lp '
            'JOIN "students" s ON s.id = lp.student_id '
            'JOIN "users" u ON u.id = s.user_id '
            'JOIN "lessons" l ON l.id = lp.lesson_id '
            'WHERE l.tutor_id = :tid AND l.start_time >= :from AND l.start_time < :to',
            {"tid": tutor_id, "from": range_start, "to": range_end},
        )
        by_lesson: dict[int, list] = {}
        for row in participations:
            by_lesson.setdefault(row["lesson_id"], []).append(row)

        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        live_price = {
            c["student_id"]: (c["hourly_rate"], c["discount"]) for c in configs
        }

        now = datetime.datetime.now()
        result = []
        cancelled_by_student = 0
        cancelled_by_tutor = 0
        for lesson in lessons:
            start, end = to_dt(lesson["start_time"]), to_dt(lesson["end_time"])
            current = lesson.get("status") or "SCHEDULED"
            status = resolve_lesson_status(current, start, end, now) or current
            parsed = parse_row("lessons", lesson)
            students = []
            total = 0
            for row in by_lesson.get(lesson["id"], []):
                if wanted_students and row["student_id"] not in wanted_students:
                    continue
                settings = parse_row(
                    "lesson_participants",
                    {"participant_settings": row.get("participant_settings")},
                )["participant_settings"] or {}
                # Отменённые записи в детализации не показываем
                # (видны только в агрегированной статистике).
                cancelled = cancellation_of(settings)
                if cancelled is not None:
                    if cancelled.get("by") == "student":
                        cancelled_by_student += 1
                    else:
                        cancelled_by_tutor += 1
                    continue
                snapshot = settings.get("price_snapshot") or {}
                if snapshot.get("final_per_hour") is not None:
                    price, estimated = int(snapshot["final_per_hour"]), False
                elif row["student_id"] in live_price:
                    rate, discount = live_price[row["student_id"]]
                    price, estimated = final_price_per_hour(rate, discount), True
                else:
                    price, estimated = 0, True
                amount = amount_for_line(start, end, price)
                students.append(LessonDetailStudent(
                    student_id=row["student_id"],
                    student_user_id=row.get("user_id") or 0,
                    student_name=row.get("full_name") or f"Ученик #{row['student_id']}",
                    amount=amount,
                    estimated=estimated,
                    paid=bool(settings.get("paid", False)),
                ))
                total += amount
            if wanted_students and not students:
                continue
            result.append(LessonDetailRow(
                lesson_id=lesson["id"],
                date=start.date().isoformat(),
                start=start.strftime("%H:%M"),
                end=end.strftime("%H:%M"),
                minutes=int(round((end - start).total_seconds() / 60)),
                is_group=bool(lesson.get("is_group")),
                status=status,
                descriptions=lesson.get("lesson_descriptions"),
                links=parsed.get("lesson_links") or [],
                students=students,
                total=total,
            ))
        return TutorLessonDetailsResponse(
            lessons=result,
            cancelled_by_student=cancelled_by_student,
            cancelled_by_tutor=cancelled_by_tutor,
        )
