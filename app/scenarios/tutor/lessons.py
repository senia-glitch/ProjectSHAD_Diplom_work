from app.utils.clock import utc_now, to_utc_naive
import datetime
from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.json_codec import serialize_for_db, parse_row
from app.utils.participants import (
    build_cancellation,
    cancellation_of,
    final_price_per_hour,
    is_cancelled_row,
)
from app.utils.db_errors import is_unique_violation
from app.utils.safe_parse import parse_iso_datetime, parse_range
from app.utils.lessons import (
    validate_lesson_times,
    build_lesson_create_data,
    build_lesson_update_data,
    resolve_lesson_status,
    check_lesson_overlap,
    resolve_effective_interval,
    tutor_schedule_lock,
    status_event,
    with_status_event,
    TERMINAL_LESSON_STATUSES,
    MANUAL_LESSON_STATUSES,
)
from app.utils.notifications import notify_participants, format_lesson_time, get_user_name
from app.utils.lesson_view import absence_note, status_history, status_note
from app.utils.statistics import amount_for_line

from core.dto import BaseDTO


class TutorGetMyLessonsDTO(BaseDTO):
    date_from: str | None = None
    date_to: str | None = None


class TutorLessonItem(BaseModel):
    lesson_id: int
    tutor_id: int
    start_time: str
    end_time: str
    is_group: bool
    lesson_links: list[dict] | None = None
    status: str = "SCHEDULED"
    status_note: dict | None = None
    absence: dict | None = None


class TutorGetMyLessonsResponse(BaseModel):
    lessons: list[TutorLessonItem]


class TutorGetLessonDTO(BaseDTO):
    lesson_id: int


class TutorLessonStudent(BaseModel):
    student_id: int
    student_user_id: int = 0
    student_name: str
    amount: int
    estimated: bool
    paid: bool = False
    cancelled: bool = False
    cancelled_by: str | None = None
    cancelled_at: str | None = None
    cancel_reason: str | None = None


class TutorGetLessonResponse(BaseModel):
    lesson_id: int
    tutor_id: int
    start_time: str
    end_time: str
    is_group: bool
    status: str
    descriptions: str | None = None
    links: list[dict] = []
    metadata: dict | None = None
    students: list[TutorLessonStudent] = []
    total: int = 0
    status_note: dict | None = None
    absence: dict | None = None
    status_history: list[dict] = []


class TutorCreateLessonDTO(BaseDTO):
    start_time: str
    end_time: str
    is_group: bool = False
    lesson_descriptions: str | None = None
    lesson_settings: dict | None = None
    lesson_links: list[dict] | None = None
    lesson_metadata: dict | None = None


class TutorCreateLessonResponse(BaseModel):
    lesson_id: int
    tutor_id: int
    start_time: str
    end_time: str
    is_group: bool
    lesson_links: list[dict] | None = None
    status: str = "SCHEDULED"


class TutorUpdateLessonDTO(BaseDTO):
    lesson_id: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_group: bool | None = None
    lesson_descriptions: str | None = None
    lesson_settings: dict | None = None
    lesson_links: list[dict] | None = None
    lesson_metadata: dict | None = None
    status: str | None = None
    # Причина смены статуса (отмена, неявка, завершение) — в историю и ученику.
    reason: str | None = Field(default=None, max_length=500)


class TutorUpdateLessonResponse(BaseModel):
    lesson_id: int
    start_time: str
    end_time: str
    is_group: bool
    lesson_links: list[dict] | None = None
    status: str = "SCHEDULED"


class TutorDeleteLessonDTO(BaseDTO):
    lesson_id: int


class TutorDeleteLessonResponse(BaseModel):
    ok: bool


@register_scenario("tutor_get_my_lessons", dto=TutorGetMyLessonsDTO, response=TutorGetMyLessonsResponse)
@tracked_scenario("tutor_get_my_lessons")
class TutorGetMyLessonsScenario(BaseScenario):
    async def execute(self, dto: TutorGetMyLessonsDTO) -> TutorGetMyLessonsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        sql = 'SELECT * FROM "lessons" WHERE tutor_id = :tid'
        params: dict = {"tid": tutor_id}
        if dto.date_from and dto.date_to:
            start, end = parse_range(dto.date_from, dto.date_to)
            sql += ' AND start_time < :dt AND end_time > :df'
            params.update({"df": start, "dt": end})
        sql += ' ORDER BY start_time LIMIT :lim OFFSET :off'
        params["lim"] = dto.limit
        params["off"] = dto.offset

        rows = await self._db.query(sql, params)
        own_settings = await _own_settings(self._db, tutor_id)

        now = utc_now()
        lessons = []
        for l in rows:
            new_status = resolve_lesson_status(
                l.get("status"), _to_dt(l["start_time"]), _to_dt(l["end_time"]), now
            )
            if new_status is not None:
                l = {**l, "status": new_status}
            lessons.append(TutorLessonItem(
                lesson_id=l["id"],
                tutor_id=l["tutor_id"],
                start_time=str(l["start_time"]),
                end_time=str(l["end_time"]),
                is_group=l["is_group"],
                lesson_links=parse_row("lessons", l).get("lesson_links"),
                status=l.get("status") or "SCHEDULED",
                status_note=status_note(l),
                absence=absence_note(l, own_settings),
            ))

        return TutorGetMyLessonsResponse(lessons=lessons)


@register_scenario("tutor_get_lesson", dto=TutorGetLessonDTO, response=TutorGetLessonResponse)
@tracked_scenario("tutor_get_lesson")
class TutorGetLessonScenario(BaseScenario):
    async def execute(self, dto: TutorGetLessonDTO) -> TutorGetLessonResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        lessons = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid AND tutor_id = :tid',
            {"lid": dto.lesson_id, "tid": tutor_id},
        )
        if not lessons:
            raise NotFoundError("Lesson not found or access denied")
        lesson = lessons[0]
        start, end = _to_dt(lesson["start_time"]), _to_dt(lesson["end_time"])
        now = utc_now()

        participations = await self._db.query(
            'SELECT lp.lesson_id, lp.student_id, lp.participant_settings, u.full_name, s.user_id '
            'FROM "lesson_participants" lp '
            'JOIN "students" s ON s.id = lp.student_id '
            'JOIN "users" u ON u.id = s.user_id '
            'WHERE lp.lesson_id = :lid',
            {"lid": dto.lesson_id},
        )
        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        live_price = {
            c["student_id"]: (c["hourly_rate"], c["discount"]) for c in configs
        }

        students = []
        total = 0
        for row in participations:
            settings = parse_row(
                "lesson_participants",
                {"participant_settings": row.get("participant_settings")},
            )["participant_settings"] or {}
            snapshot = settings.get("price_snapshot") or {}
            cancelled = cancellation_of(settings)
            if snapshot.get("final_per_hour") is not None:
                price, estimated = int(snapshot["final_per_hour"]), False
            elif row["student_id"] in live_price:
                rate, discount = live_price[row["student_id"]]
                price, estimated = final_price_per_hour(rate, discount), True
            else:
                price, estimated = 0, True
            amount = amount_for_line(start, end, price)
            if cancelled is None:
                total += amount
            students.append(TutorLessonStudent(
                student_id=row["student_id"],
                student_user_id=row.get("user_id") or 0,
                student_name=row.get("full_name") or f"Ученик #{row['student_id']}",
                amount=amount,
                estimated=estimated,
                paid=bool(settings.get("paid", False)),
                cancelled=cancelled is not None,
                cancelled_by=(cancelled or {}).get("by"),
                cancelled_at=(cancelled or {}).get("at"),
                cancel_reason=(cancelled or {}).get("reason"),
            ))
        lesson_now = {**lesson, "status": resolve_lesson_status(lesson.get("status"), start, end, now)
                      or lesson.get("status") or "SCHEDULED"}
        own_settings = await _own_settings(self._db, tutor_id)

        return TutorGetLessonResponse(
            lesson_id=lesson["id"],
            tutor_id=tutor_id,
            start_time=str(lesson["start_time"]),
            end_time=str(lesson["end_time"]),
            is_group=bool(lesson.get("is_group")),
            status=resolve_lesson_status(lesson.get("status"), start, end, now)
            or lesson.get("status") or "SCHEDULED",
            descriptions=lesson.get("lesson_descriptions"),
            links=parse_row("lessons", lesson).get("lesson_links") or [],
            metadata=parse_row("lessons", lesson).get("lesson_metadata"),
            students=students,
            total=total,
            status_note=status_note(lesson_now),
            absence=absence_note(lesson, own_settings),
            status_history=status_history(lesson),
        )


@register_scenario("tutor_create_lesson", dto=TutorCreateLessonDTO, response=TutorCreateLessonResponse)
@tracked_scenario("tutor_create_lesson")
class TutorCreateLessonScenario(BaseScenario):
    async def execute(self, dto: TutorCreateLessonDTO) -> TutorCreateLessonResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        start_time = parse_iso_datetime(dto.start_time, "start_time")
        end_time = parse_iso_datetime(dto.end_time, "end_time")

        validate_lesson_times(start_time, end_time)

        # Создание урока сериализуем локом репетитора: пересечения
        # проверяются и фиксируются атомарно в рамках процесса.
        async with (await tutor_schedule_lock(tutor_id)):

            # Сторож пересечений: новый урок не должен пересекаться
            # с существующими уроками репетитора. Интервал полуоткрытый
            # [start, end): стык конец-в-конец разрешён. Тот же приём,
            # что у броней (tutor_create_booking).
            overlapping = await self._db.query(
                'SELECT id FROM "lessons" WHERE tutor_id = :tid AND start_time < :et AND end_time > :st '
                "AND (status IS NULL OR status NOT IN ('CANCELLED', 'REJECTED', 'PENDING'))",
                {"tid": tutor_id, "et": end_time, "st": start_time},
            )
            check_lesson_overlap(overlapping)

            # Ссылки по умолчанию — из своих настроек, если явно не переданы.
            # Участников на момент создания ещё нет, конфигурацию выбрать не из чего.
            lesson_links = dto.lesson_links
            if lesson_links is None:
                settings_rows = await self._db.query(
                    'SELECT * FROM "tutor_settings" WHERE tutor_id = :tid',
                    {"tid": tutor_id},
                )
                if settings_rows:
                    lesson_links = parse_row("tutor_settings", settings_rows[0]).get("default_links")

            lesson_data = build_lesson_create_data(
                tutor_id=tutor_id,
                created_by_id=token.user_id,
                start_time=start_time,
                end_time=end_time,
                is_group=dto.is_group,
                lesson_descriptions=dto.lesson_descriptions,
                lesson_settings=dto.lesson_settings,
                lesson_links=lesson_links,
                lesson_metadata=dto.lesson_metadata,
            )
            lesson_data["status_history"] = [status_event("SCHEDULED", "tutor", actor_user_id=token.user_id)]
            lesson_data = serialize_for_db("lessons", lesson_data)

            try:
                lesson = await self._db.create("lessons", lesson_data)
            except Exception as e:
                if is_unique_violation(e):
                    raise ConflictError("Lesson already exists")
                raise
            return TutorCreateLessonResponse(
                lesson_id=lesson["id"],
                tutor_id=tutor_id,
                start_time=str(lesson["start_time"]),
                end_time=str(lesson["end_time"]),
                is_group=lesson["is_group"],
                lesson_links=lesson_links,
                status=lesson.get("status") or "SCHEDULED",
            )


@register_scenario("tutor_update_lesson", dto=TutorUpdateLessonDTO, response=TutorUpdateLessonResponse)
@tracked_scenario("tutor_update_lesson")
class TutorUpdateLessonScenario(BaseScenario):
    async def execute(self, dto: TutorUpdateLessonDTO) -> TutorUpdateLessonResponse:
        if dto.lesson_id is None:
            raise ValidationError("lesson_id is required")
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        # Обновление (время/статус) сериализуем локом репетитора:
        # иначе параллельные переносы дают пересекающиеся уроки.
        async with (await tutor_schedule_lock(tutor_id)):
            lessons = await self._db.query(
                'SELECT * FROM "lessons" WHERE id = :lid AND tutor_id = :tid',
                {"lid": dto.lesson_id, "tid": tutor_id},
            )
            if not lessons:
                raise NotFoundError("Lesson not found or access denied")
            current_status = lessons[0].get("status") or "SCHEDULED"

            # Ручные статусы: только FINISHED/CANCELLED/NO_SHOW, только из
            # нетерминального. Время терминального урока править нельзя.
            if dto.status is not None:
                if dto.status not in MANUAL_LESSON_STATUSES:
                    raise ValidationError(
                        f"Invalid status: {dto.status}. Must be one of: {', '.join(sorted(MANUAL_LESSON_STATUSES))}"
                    )
                if current_status in TERMINAL_LESSON_STATUSES:
                    raise ValidationError(f"Lesson is already {current_status}")
            if current_status in TERMINAL_LESSON_STATUSES and (
                dto.start_time is not None or dto.end_time is not None
            ):
                raise ValidationError(f"Cannot change time of lesson in status {current_status}")

            # Сторож пересечений при переносе: эффективный интервал урока
            # (с учётом правки одной или обеих границ) не должен пересекаться
            # с другими уроками репетитора. Сам урок исключается (id != :lid).
            eff_start, eff_end, time_changed = resolve_effective_interval(
                _to_dt(lessons[0]["start_time"]),
                _to_dt(lessons[0]["end_time"]),
                parse_iso_datetime(dto.start_time, "start_time") if dto.start_time is not None else None,
                parse_iso_datetime(dto.end_time, "end_time") if dto.end_time is not None else None,
            )
            if time_changed:
                # Полная проверка эффективного интервала: и при правке одной
                # границы урок нельзя увести в прошлое или растянуть > 168 ч.
                validate_lesson_times(eff_start, eff_end)
                overlapping = await self._db.query(
                    'SELECT id FROM "lessons" WHERE tutor_id = :tid AND start_time < :et AND end_time > :st AND id != :lid '
                    "AND (status IS NULL OR status NOT IN ('CANCELLED', 'REJECTED', 'PENDING'))",
                    {"tid": tutor_id, "et": eff_end, "st": eff_start, "lid": dto.lesson_id},
                )
                check_lesson_overlap(overlapping)

            if dto.status is not None:
                history = parse_row("lessons", lessons[0]).get("status_history")
                event = status_event(dto.status, "tutor", actor_user_id=token.user_id, reason=dto.reason)
                history_update = {"status_history": with_status_event(history, event)}
            else:
                history_update = {}

            update_data = build_lesson_update_data({
                "start_time": dto.start_time,
                "end_time": dto.end_time,
                "is_group": dto.is_group,
                "lesson_descriptions": dto.lesson_descriptions,
                "lesson_settings": dto.lesson_settings,
                "lesson_links": dto.lesson_links,
                "lesson_metadata": dto.lesson_metadata,
                "status": dto.status,
            })

            update_data.update(history_update)
            if update_data:
                update_data = serialize_for_db("lessons", update_data)
                await self._db.update("lessons", dto.lesson_id, update_data)

            if dto.status is not None:
                labels = {"CANCELLED": "отменён", "NO_SHOW": "неявка", "FINISHED": "завершён"}
                tutor_name = await get_user_name(self._db, token.user_id)
                reason = f". Причина: {dto.reason.strip()}" if dto.reason and dto.reason.strip() else ""
                await notify_participants(
                    self._db, dto.lesson_id, "lesson_status_changed",
                    f"Репетитор {tutor_name} отметил урок {format_lesson_time(eff_start)}: {labels[dto.status]}{reason}",
                )
            elif time_changed:
                tutor_name = await get_user_name(self._db, token.user_id)
                await notify_participants(
                    self._db, dto.lesson_id, "lesson_rescheduled",
                    f"Репетитор {tutor_name} перенёс урок с {format_lesson_time(lessons[0]['start_time'])} "
                    f"на {format_lesson_time(eff_start)}",
                )

            # Отмена урока помечает все активные записи репетитором.
            # Уже отменённые (например, вышедшими учениками) не перезаписываем.
            if dto.status == "CANCELLED":
                for p in await self._db.query(
                    'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid',
                    {"lid": dto.lesson_id},
                ):
                    if is_cancelled_row(p):
                        continue
                    settings = parse_row("lesson_participants", p).get("participant_settings") or {}
                    settings["cancelled"] = build_cancellation(
                        "tutor", actor_user_id=token.user_id, reason=dto.reason,
                    )
                    await self._db.update(
                        "lesson_participants",
                        p["id"],
                        serialize_for_db("lesson_participants", {"participant_settings": settings}),
                    )

            updated = await self._db.query(
                'SELECT * FROM "lessons" WHERE id = :lid',
                {"lid": dto.lesson_id},
            )
            if not updated:
                raise NotFoundError("Lesson not found")
            u = parse_row("lessons", updated[0])
            now = utc_now()
            new_status = resolve_lesson_status(
                u.get("status"), _to_dt(u["start_time"]), _to_dt(u["end_time"]), now
            )
            if new_status is not None and new_status != u.get("status"):
                await self._db.update("lessons", dto.lesson_id, {"status": new_status})
                u = {**u, "status": new_status}

            return TutorUpdateLessonResponse(
                lesson_id=u["id"],
                start_time=str(u["start_time"]),
                end_time=str(u["end_time"]),
                is_group=u["is_group"],
                lesson_links=u.get("lesson_links"),
                status=u.get("status") or "SCHEDULED",
            )


@register_scenario("tutor_delete_lesson", dto=TutorDeleteLessonDTO, response=TutorDeleteLessonResponse)
@tracked_scenario("tutor_delete_lesson")
class TutorDeleteLessonScenario(BaseScenario):
    async def execute(self, dto: TutorDeleteLessonDTO) -> TutorDeleteLessonResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor not found")
        tutor_id = tutors[0]["id"]

        lessons = await self._db.query(
            'SELECT id FROM "lessons" WHERE id = :lid AND tutor_id = :tid',
            {"lid": dto.lesson_id, "tid": tutor_id},
        )
        if not lessons:
            raise NotFoundError("Lesson not found or access denied")

        await self._db.query(
            'DELETE FROM "lesson_participants" WHERE lesson_id = :lid',
            {"lid": dto.lesson_id},
            channel="write",
        )
        await self._db.delete("lessons", dto.lesson_id)

        return TutorDeleteLessonResponse(ok=True)


async def _own_settings(db, tutor_id: int) -> dict:
    rows = await db.query('SELECT * FROM "tutor_settings" WHERE tutor_id = :tid', {"tid": tutor_id})
    return rows[0] if rows else {}


def _to_dt(value) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return to_utc_naive(value)
    if isinstance(value, str):
        return parse_iso_datetime(value.replace(" ", "T"), "datetime")
    return value
