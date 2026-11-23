import datetime
from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO

from app.utils.json_codec import parse_row
from app.utils.safe_parse import parse_iso_date, to_dt
from app.utils.lessons import resolve_lesson_status
from app.utils.participants import final_price_per_hour, cancellation_of
from app.utils.statistics import (
    GRANULARITIES,
    aggregate,
    amount_for_line,
    capacity_stats,
    time_range_hours,
)

# Защита от случайной сверхвыборки: год уроков одного репетитора
# в реальности — сотни строк, лимит с запасом.


class TutorGetStatisticsDTO(BaseDTO):
    year: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    granularity: str | None = None
    student_ids: str | None = None


class StatisticsTotals(BaseModel):
    lessons: int
    tutor_hours: float
    billed_hours: float
    revenue: int
    forecast_lessons: int
    forecast_revenue: int
    forecast_hours: float
    cancelled_lessons: int
    no_show_lessons: int
    lost_revenue: int = 0
    estimated_lines: int
    # Отмены записей по инициаторам (строки участия, не уроки).
    cancelled_by_student: int = 0
    cancelled_by_tutor: int = 0


class StatisticsSeriesRow(BaseModel):
    bucket: str
    bucket_start: str
    lessons: int
    revenue: int
    tutor_hours: float
    forecast_lessons: int
    forecast_revenue: int
    forecast_hours: float


class StatisticsStudentRow(BaseModel):
    student_id: int
    student_name: str
    lessons: int
    billed_hours: float
    revenue: int
    forecast_revenue: int
    forecast_lessons: int = 0
    forecast_hours: float = 0.0
    cancelled: int
    no_show: int = 0
    lost_revenue: int = 0
    estimated: int
    first_lesson: str | None = None
    last_lesson: str | None = None
    # Статус ученика из его настроек (ACTIVE/INACTIVE), не эвристика.
    status: str = "ACTIVE"


class StatisticsMeta(BaseModel):
    year: int
    date_from: str
    date_to: str
    granularity: str
    student_ids: list[int]


class StatisticsWeekdayRow(BaseModel):
    weekday: int
    lessons: int
    revenue: int


class StatisticsHourCell(BaseModel):
    weekday: int
    hour: int
    lessons: int
    revenue: int


class StatisticsStudentWeekdayCell(BaseModel):
    student_id: int
    weekday: int
    lessons: int
    revenue: int


class StatisticsStudentMonthCell(BaseModel):
    student_id: int
    bucket: str
    revenue: int


class StatisticsStudentSeriesCell(BaseModel):
    student_id: int
    bucket: str
    revenue: int
    forecast: int
    lessons: int = 0
    forecast_lessons: int = 0
    tutor_hours: float = 0.0
    forecast_hours: float = 0.0


class UpcomingStudent(BaseModel):
    student_id: int
    student_name: str
    amount: int
    estimated: bool


class UpcomingRow(BaseModel):
    lesson_id: int
    date: str
    start: str
    end: str
    minutes: int
    is_group: bool
    students: list[UpcomingStudent]
    total: int


class StatisticsCapacity(BaseModel):
    weekly_open_hours: float
    estimated_open_hours: float
    occupancy_pct: int | None = None


class TutorGetStatisticsResponse(BaseModel):
    totals: StatisticsTotals
    series: list[StatisticsSeriesRow]
    by_student: list[StatisticsStudentRow]
    by_weekday: list[StatisticsWeekdayRow]
    by_hour: list[StatisticsHourCell] = []
    by_student_weekday: list[StatisticsStudentWeekdayCell] = []
    by_student_month: list[StatisticsStudentMonthCell] = []
    by_student_series: list[StatisticsStudentSeriesCell] = []
    upcoming: list[UpcomingRow] = []
    capacity: StatisticsCapacity
    meta: StatisticsMeta


def _parse_student_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        raise ValidationError("Invalid student_ids: expected comma-separated integers")


@register_scenario("tutor_get_statistics")
@tracked_scenario("tutor_get_statistics")
class TutorGetStatisticsScenario(BaseScenario):
    async def execute(self, dto: TutorGetStatisticsDTO) -> TutorGetStatisticsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        now = datetime.datetime.now()
        year = dto.year if dto.year is not None else now.year
        if not 2000 <= year <= 2100:
            raise ValidationError("Invalid year")

        date_from = parse_iso_date(dto.date_from, "date_from") if dto.date_from else datetime.date(year, 1, 1)
        date_to = parse_iso_date(dto.date_to, "date_to") if dto.date_to else datetime.date(year, 12, 31)
        if date_from.year != year or date_to.year != year:
            raise ValidationError("Dates must belong to the requested year")
        if date_from > date_to:
            raise ValidationError("date_from must not be greater than date_to")

        granularity = dto.granularity or "auto"
        if granularity != "auto" and granularity not in GRANULARITIES:
            raise ValidationError(f"Invalid granularity: {granularity}")
        wanted_students = set(_parse_student_ids(dto.student_ids))

        range_start = datetime.datetime.combine(date_from, datetime.time.min)
        range_end = datetime.datetime.combine(
            date_to + datetime.timedelta(days=1), datetime.time.min
        )

        lessons = await self._db.query(
            'SELECT id, start_time, end_time, status FROM "lessons" '
            'WHERE tutor_id = :tid AND start_time >= :from AND start_time < :to '
            'ORDER BY start_time LIMIT 5000',
            {"tid": tutor_id, "from": range_start, "to": range_end},
        )
        by_lesson = {lesson["id"]: lesson for lesson in lessons}

        participations = await self._db.query(
            'SELECT lp.lesson_id, lp.student_id, lp.participant_settings, '
            'l.start_time, l.end_time, l.status, u.full_name '
            'FROM "lesson_participants" lp '
            'JOIN "lessons" l ON l.id = lp.lesson_id '
            'JOIN "students" s ON s.id = lp.student_id '
            'JOIN "users" u ON u.id = s.user_id '
            'WHERE l.tutor_id = :tid AND l.start_time >= :from AND l.start_time < :to',
            {"tid": tutor_id, "from": range_start, "to": range_end},
        )

        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        live_price = {
            c["student_id"]: (c["hourly_rate"], c["discount"]) for c in configs
        }

        # История каждого ученика за всё время (первая/последняя встреча) —
        # одним запросом, вне зависимости от выбранного периода.
        # Отменённые записи встречами не считаем (фильтр в Python:
        # cancelled живёт в JSON и в GROUP BY его не отфильтровать).
        history_rows = await self._db.query(
            'SELECT lp.student_id, l.start_time, lp.participant_settings '
            'FROM "lesson_participants" lp '
            'JOIN "lessons" l ON l.id = lp.lesson_id '
            'WHERE l.tutor_id = :tid',
            {"tid": tutor_id},
        )
        bounds: dict[int, list] = {}
        for row in history_rows:
            settings = parse_row(
                "lesson_participants", {"participant_settings": row.get("participant_settings")}
            )["participant_settings"] or {}
            if cancellation_of(settings) is not None:
                continue
            st = to_dt(row["start_time"])
            cur = bounds.get(row["student_id"])
            if cur is None:
                bounds[row["student_id"]] = [st, st]
            else:
                cur[0] = min(cur[0], st)
                cur[1] = max(cur[1], st)
        student_history = {
            sid: (b[0].date().isoformat(), b[1].date().isoformat())
            for sid, b in bounds.items()
        }

        # Статус учеников из их настроек — одним запросом по связям.
        # Схемы не меняем. Нет настроек — считаем ACTIVE.
        status_rows = await self._db.query(
            'SELECT st.student_id, st.status FROM "student_settings" st '
            'JOIN "configurations" c ON c.student_id = st.student_id '
            'WHERE c.tutor_id = :tid',
            {"tid": tutor_id},
        )
        student_status = {
            row["student_id"]: (row.get("status") or "ACTIVE")
            for row in status_rows
        }

        lines = []
        cancelled_by_student = 0
        cancelled_by_tutor = 0
        for row in participations:
            if row["lesson_id"] not in by_lesson:
                continue
            if wanted_students and row["student_id"] not in wanted_students:
                continue
            settings = parse_row(
                "lesson_participants", {"participant_settings": row.get("participant_settings")}
            )["participant_settings"] or {}
            # Отменённые записи в деньги/часы не идут, только в счётчики инициатив.
            cancelled = settings.get("cancelled") if isinstance(settings.get("cancelled"), dict) else None
            if cancelled is not None:
                if cancelled.get("by") == "student":
                    cancelled_by_student += 1
                else:
                    cancelled_by_tutor += 1
                continue
            start, end = to_dt(row["start_time"]), to_dt(row["end_time"])
            current = row.get("status") or "SCHEDULED"
            effective = resolve_lesson_status(current, start, end, now) or current
            snapshot = settings.get("price_snapshot") or {}
            if snapshot.get("final_per_hour") is not None:
                price, estimated = int(snapshot["final_per_hour"]), False
            elif row["student_id"] in live_price:
                rate, discount = live_price[row["student_id"]]
                price, estimated = final_price_per_hour(rate, discount), True
            else:
                price, estimated = 0, True
            lines.append({
                "lesson_id": row["lesson_id"],
                "student_id": row["student_id"],
                "student_name": row.get("full_name"),
                "start": start,
                "end": end,
                "status": effective,
                "final_per_hour": price,
                "estimated": estimated,
            })

        result = aggregate(lines, date_from, date_to, granularity)
        result["totals"]["cancelled_by_student"] = cancelled_by_student
        result["totals"]["cancelled_by_tutor"] = cancelled_by_tutor

        # Будущие занятия на 4 недели вперёд — для секции прогноза.
        # Отдельный запрос от сегодня, не зависит от выбранного периода.
        upcoming: list[UpcomingRow] = []
        future_from = datetime.datetime.combine(now.date(), datetime.time.min)
        future_to = future_from + datetime.timedelta(days=28)
        future_rows = await self._db.query(
            'SELECT lp.lesson_id, lp.student_id, lp.participant_settings, '
            'l.start_time, l.end_time, l.is_group, u.full_name '
            'FROM "lesson_participants" lp '
            'JOIN "lessons" l ON l.id = lp.lesson_id '
            'JOIN "students" s ON s.id = lp.student_id '
            'JOIN "users" u ON u.id = s.user_id '
            'WHERE l.tutor_id = :tid AND l.start_time >= :from AND l.start_time < :to '
            'AND (l.status = :s1 OR l.status = :s2) '
            'ORDER BY l.start_time LIMIT 500',
            {"tid": tutor_id, "from": future_from, "to": future_to,
             "s1": "SCHEDULED", "s2": "ONGOING"},
        )
        upcoming_by_lesson: dict[int, dict] = {}
        for row in future_rows:
            if wanted_students and row["student_id"] not in wanted_students:
                continue
            settings = parse_row(
                "lesson_participants", {"participant_settings": row.get("participant_settings")}
            )["participant_settings"] or {}
            # Отменённые записи в прогнозе не показываем.
            if cancellation_of(settings) is not None:
                continue
            start, end = to_dt(row["start_time"]), to_dt(row["end_time"])
            snapshot = settings.get("price_snapshot") or {}
            if snapshot.get("final_per_hour") is not None:
                price, estimated = int(snapshot["final_per_hour"]), False
            elif row["student_id"] in live_price:
                rate, discount = live_price[row["student_id"]]
                price, estimated = final_price_per_hour(rate, discount), True
            else:
                price, estimated = 0, True
            entry = upcoming_by_lesson.get(row["lesson_id"])
            if entry is None:
                entry = {
                    "lesson_id": row["lesson_id"],
                    "date": start.date().isoformat(),
                    "start": start.strftime("%H:%M"),
                    "end": end.strftime("%H:%M"),
                    "minutes": int(round((end - start).total_seconds() / 60)),
                    "is_group": bool(row.get("is_group")),
                    "students": [],
                    "total": 0,
                }
                upcoming_by_lesson[row["lesson_id"]] = entry
            amount = amount_for_line(start, end, price)
            entry["students"].append(UpcomingStudent(
                student_id=row["student_id"],
                student_name=row.get("full_name") or f"Ученик #{row['student_id']}",
                amount=amount,
                estimated=estimated,
            ))
            entry["total"] += amount
        upcoming = [UpcomingRow(**entry) for entry in upcoming_by_lesson.values()]

        # Занятость: недельная норма открытых часов по броням.
        # Брони — повторяющиеся правила, время в БД лежит без даты.
        bookings = await self._db.query(
            'SELECT start_time, end_time FROM "bookings" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        weekly_open = 0.0
        for booking in bookings:
            try:
                weekly_open += time_range_hours(booking["start_time"], booking["end_time"])
            except (ValueError, TypeError):
                continue
        capacity = capacity_stats(
            weekly_open,
            (date_to - date_from).days + 1,
            result["totals"]["tutor_hours"],
        )

        by_student = []
        for row in result["by_student"]:
            first, last = student_history.get(row["student_id"], (None, None))
            by_student.append(StatisticsStudentRow(
                **row, first_lesson=first, last_lesson=last,
                status=student_status.get(row["student_id"], "ACTIVE"),
            ))

        return TutorGetStatisticsResponse(
            totals=StatisticsTotals(**result["totals"]),
            series=[StatisticsSeriesRow(**r) for r in result["series"]],
            by_student=by_student,
            by_weekday=[StatisticsWeekdayRow(**r) for r in result["by_weekday"]],
            by_hour=[StatisticsHourCell(**r) for r in result["by_hour"]],
            by_student_weekday=[StatisticsStudentWeekdayCell(**r) for r in result["by_student_weekday"]],
            by_student_month=[StatisticsStudentMonthCell(**r) for r in result["by_student_month"]],
            by_student_series=[StatisticsStudentSeriesCell(**r) for r in result["by_student_series"]],
            upcoming=upcoming,
            capacity=StatisticsCapacity(**capacity),
            meta=StatisticsMeta(
                year=year,
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat(),
                granularity=result["granularity"],
                student_ids=sorted(wanted_students),
            ),
        )
