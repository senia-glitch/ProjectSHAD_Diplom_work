from app.utils.clock import utc_now, to_utc_naive
import datetime
from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.core.exceptions import ForbiddenError
from app.utils.json_codec import serialize_for_db, parse_int_list, parse_row
from app.utils.db_errors import is_unique_violation
from app.utils.participants import (
    build_price_snapshot,
    build_cancellation,
    is_cancelled_row,
    validate_lesson_not_terminal,
    validate_cancellation_deadline,
)
from app.utils.safe_parse import parse_iso_datetime, parse_iso_date, parse_range
from app.utils.lesson_view import absence_note, personal_status, status_note, status_history as lesson_status_history
from app.utils.schedule import get_available_slots, merge_lessons, subtract_blocks
from app.utils.notifications import notify_user, get_user_name, get_tutor_user_id, format_lesson_time
from app.utils.lessons import (
    validate_lesson_times,
    validate_booking_lead_time,
    check_slot_availability,
    build_lesson_create_data,
    resolve_lesson_status,
    tutor_schedule_lock,
    status_event,
    with_status_event,
    TERMINAL_LESSON_STATUSES,
)
from app.scenarios.student.availability import free_windows
from core.dto import BaseDTO


async def _tutor_absences(db, tutor_ids: set) -> dict:
    """Настройки отсутствия репетиторов по tutor_id (для пометки уроков)."""
    result = {}
    for tutor_id in tutor_ids:  # репетиторов у ученика единицы
        rows = await db.query(
            'SELECT tutor_id, absence_status, absence_from, absence_to FROM "tutor_settings" '
            'WHERE tutor_id = :tid',
            {"tid": tutor_id},
        )
        if rows:
            result[tutor_id] = rows[0]
    return result


async def _notify_tutor(db, tutor_id: int, ntype: str, text: str) -> None:
    """Уведомление репетитора (user_id берём по tutor_id); best-effort."""
    tutor_user_id = await get_tutor_user_id(db, tutor_id)
    if tutor_user_id is not None:
        await notify_user(db, tutor_user_id, ntype, text)


async def _notify_join(db, lesson_id: int, student_user_id: int) -> None:
    """Уведомление репетитора о вступлении ученика в его урок."""
    lessons = await db.query(
        'SELECT * FROM "lessons" WHERE id = :lid',
        {"lid": lesson_id},
    )
    if not lessons:
        return
    student_name = await get_user_name(db, student_user_id)
    await _notify_tutor(
        db, lessons[0]["tutor_id"], "lesson_joined",
        f"Ученик {student_name} вступил в урок {format_lesson_time(lessons[0]['start_time'])}",
    )


class StudentGetMyLessonsDTO(BaseDTO):
    date_from: str | None = None
    date_to: str | None = None


class LessonItem(BaseModel):
    lesson_id: int
    tutor_id: int
    start_time: str
    end_time: str
    is_group: bool
    lesson_links: list[dict] | None = None
    status: str = "SCHEDULED"
    # Кто/когда/почему изменил статус (отмена, заявка, отклонение, закрытие системой).
    status_note: dict | None = None
    # Урок пришёлся на отпуск/болезнь репетитора: заморожен, не отменён.
    absence: dict | None = None


class StudentGetMyLessonsResponse(BaseModel):
    lessons: list[LessonItem]


class StudentGetLessonDTO(BaseDTO):
    lesson_id: int


class StudentGetLessonResponse(BaseModel):
    lesson_id: int
    tutor_id: int
    start_time: str
    end_time: str
    is_group: bool
    lesson_links: list[dict] | None = None
    status: str = "SCHEDULED"
    status_note: dict | None = None
    absence: dict | None = None
    status_history: list[dict] = []
    # Можно ли отменить сейчас и до какого момента (наивный UTC).
    can_cancel: bool = False
    cancel_deadline: str | None = None


class StudentGetTutorLessonsDTO(BaseDTO):
    tutor_user_id: int
    date_from: str | None = None
    date_to: str | None = None


class StudentGetTutorLessonsResponse(BaseModel):
    lessons: list[LessonItem]


class StudentCreateLessonDTO(BaseDTO):
    tutor_user_id: int = Field(..., description="ID пользователя-репетитора")
    start_time: str = Field(..., description="Начало урока (ISO datetime)")
    end_time: str = Field(..., description="Конец урока (ISO datetime)")
    is_group: bool = False
    lesson_descriptions: str | None = None
    lesson_settings: dict | None = None
    lesson_links: list[dict] | None = None
    lesson_metadata: dict | None = None


class StudentCreateLessonResponse(BaseModel):
    lesson_id: int
    tutor_id: int
    start_time: str
    end_time: str
    is_group: bool
    created_by_id: int
    participant_id: int
    lesson_links: list[dict] | None = None
    status: str = "SCHEDULED"


class StudentJoinLessonDTO(BaseDTO):
    lesson_id: int


class StudentJoinLessonResponse(BaseModel):
    participant_id: int


class StudentLeaveLessonDTO(BaseDTO):
    lesson_id: int
    reason: str | None = Field(default=None, max_length=500)


class StudentLeaveLessonResponse(BaseModel):
    ok: bool


@register_scenario("student_get_my_lessons", dto=StudentGetMyLessonsDTO, response=StudentGetMyLessonsResponse)
@tracked_scenario("student_get_my_lessons")
class StudentGetMyLessonsScenario(BaseScenario):
    async def execute(self, dto: StudentGetMyLessonsDTO) -> StudentGetMyLessonsResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        participations = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE student_id = :sid',
            {"sid": student_id},
        )
        period = parse_range(dto.date_from, dto.date_to) if dto.date_from and dto.date_to else None
        rows = []
        for p in participations:
            found = await self._db.query('SELECT * FROM "lessons" WHERE id = :lid', {"lid": p["lesson_id"]})
            if not found:
                continue
            l = found[0]
            # Полуоткрытый период в UTC: урок пересекает [start, end).
            if period and not (_to_dt(l["start_time"]) < period[1] and _to_dt(l["end_time"]) > period[0]):
                continue
            rows.append((l, p))
        rows.sort(key=lambda pair: _to_dt(pair[0]["start_time"]))
        absence_by_tutor = await _tutor_absences(self._db, {l["tutor_id"] for l, _ in rows})

        lessons = []
        now = utc_now()
        for l, participant in rows:
            new_status = resolve_lesson_status(
                l.get("status"), _to_dt(l["start_time"]), _to_dt(l["end_time"]), now
            )
            if new_status is not None:
                l = {**l, "status": new_status}
            lessons.append(LessonItem(
                lesson_id=l["id"],
                tutor_id=l["tutor_id"],
                start_time=str(l["start_time"]),
                end_time=str(l["end_time"]),
                is_group=l["is_group"],
                lesson_links=parse_row("lessons", l).get("lesson_links"),
                status=personal_status(l, participant),
                status_note=status_note(l, participant),
                absence=absence_note(l, absence_by_tutor.get(l["tutor_id"])),
            ))

        return StudentGetMyLessonsResponse(lessons=lessons[dto.offset:dto.offset + dto.limit])


@register_scenario("student_get_lesson", dto=StudentGetLessonDTO, response=StudentGetLessonResponse)
@tracked_scenario("student_get_lesson")
class StudentGetLessonScenario(BaseScenario):
    async def execute(self, dto: StudentGetLessonDTO) -> StudentGetLessonResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        participations = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE student_id = :sid',
            {"sid": student_id},
        )
        mine = [p for p in participations if p["lesson_id"] == dto.lesson_id]
        # Не участник — урока для ученика не существует (в т.ч. чужой урок).
        if not mine:
            raise NotFoundError("Lesson not found or access denied")

        lesson_rows = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lesson_rows:
            raise NotFoundError("Lesson not found")
        l = lesson_rows[0]
        now = utc_now()

        new_status = resolve_lesson_status(
            l.get("status"), _to_dt(l["start_time"]), _to_dt(l["end_time"]), now
        )
        if new_status is not None:
            l = {**l, "status": new_status}
        status = personal_status(l, mine[0])

        # Отменить можно незавершённый урок: заявку — всегда, подтверждённый — до дедлайна связи.
        can_cancel, deadline = False, None
        if status not in TERMINAL_LESSON_STATUSES and status != "ONGOING":
            if status == "PENDING":
                can_cancel = True
            else:
                configs = await self._db.query(
                    'SELECT cancellation_lead_time_hours FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid',
                    {"sid": student_id, "tid": l["tutor_id"]},
                )
                lead = configs[0].get("cancellation_lead_time_hours", 0) if configs else 0
                limit = _to_dt(l["start_time"]) - datetime.timedelta(hours=lead)
                deadline = limit.isoformat()
                can_cancel = now <= limit
        absences = await _tutor_absences(self._db, {l["tutor_id"]})

        return StudentGetLessonResponse(
            lesson_id=l["id"],
            tutor_id=l["tutor_id"],
            start_time=str(l["start_time"]),
            end_time=str(l["end_time"]),
            is_group=l["is_group"],
            lesson_links=parse_row("lessons", l).get("lesson_links"),
            status=status,
            status_note=status_note(l, mine[0]),
            absence=absence_note(l, absences.get(l["tutor_id"])),
            status_history=lesson_status_history(l),
            can_cancel=can_cancel,
            cancel_deadline=deadline,
        )


@register_scenario("student_get_tutor_lessons", dto=StudentGetTutorLessonsDTO, response=StudentGetTutorLessonsResponse)
@tracked_scenario("student_get_tutor_lessons")
class StudentGetTutorLessonsScenario(BaseScenario):
    async def execute(self, dto: StudentGetTutorLessonsDTO) -> StudentGetTutorLessonsResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": dto.tutor_user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        configs = await self._db.query(
            'SELECT id FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid AND status = :active',
            {"sid": student_id, "tid": tutor_id, "active": "ACTIVE"},
        )
        if not configs:
            raise ForbiddenError("You don't have a configuration with this tutor")

        participations = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE student_id = :sid',
            {"sid": student_id},
        )
        my_lesson_ids = {
            p["lesson_id"] for p in participations if not is_cancelled_row(p)
        }

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

        now = utc_now()
        lessons = []
        for l in rows:
            new_status = resolve_lesson_status(
                l.get("status"), _to_dt(l["start_time"]), _to_dt(l["end_time"]), now
            )
            if new_status is not None:
                l = {**l, "status": new_status}
            links = parse_row("lessons", l).get("lesson_links")
            if l["id"] not in my_lesson_ids:
                links = None
            lessons.append(LessonItem(
                lesson_id=l["id"],
                tutor_id=l["tutor_id"],
                start_time=str(l["start_time"]),
                end_time=str(l["end_time"]),
                is_group=l["is_group"],
                lesson_links=links,
                status=l.get("status") or "SCHEDULED",
            ))

        return StudentGetTutorLessonsResponse(lessons=lessons)


@register_scenario("student_create_lesson", dto=StudentCreateLessonDTO, response=StudentCreateLessonResponse)
@tracked_scenario("student_create_lesson")
class StudentCreateLessonScenario(BaseScenario):
    async def execute(self, dto: StudentCreateLessonDTO) -> StudentCreateLessonResponse:
        token = extract_token_info(dto.access_token)
        student_user_id = token.user_id

        start_time = parse_iso_datetime(dto.start_time, "start_time")
        end_time = parse_iso_datetime(dto.end_time, "end_time")

        now = utc_now()
        validate_lesson_times(start_time, end_time, now=now)

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

        validate_booking_lead_time(now, start_time, config["booking_lead_time_hours"])

        # Создание урока сериализуем локом репетитора: занятость
        # проверяется и фиксируется атомарно в рамках процесса
        # (check-then-create конкуренция иначе даёт пересечения).
        async with (await tutor_schedule_lock(tutor_id)):
            # Окна вокруг запрошенного интервала: смежные окна склеиваются проверкой.
            margin = datetime.timedelta(days=1)
            free_slots = await free_windows(
                self._db, tutor_id=tutor_id, student_id=student_id, tutor_settings=ts,
                start=start_time - margin, end=end_time + margin,
            )
            if not check_slot_availability(
                start_time, end_time, free_slots, config.get("slot_step_minutes") or 60
            ):
                raise ValidationError("Requested time slot is not available")

            # Без автоподтверждения урок — заявка, ждущая решения репетитора.
            confirmed = bool(config.get("auto_confirm_bookings", True))
            initial_status = "SCHEDULED" if confirmed else "PENDING"

            # Ссылки по умолчанию — из своей конфигурации с этим репетитором.
            lesson_links = dto.lesson_links
            if lesson_links is None:
                lesson_links = parse_row("configurations", config).get("default_links")

            lesson_data = build_lesson_create_data(
                tutor_id, start_time, end_time, token.user_id,
                is_group=dto.is_group,
                lesson_descriptions=dto.lesson_descriptions,
                lesson_settings=dto.lesson_settings,
                lesson_links=lesson_links,
                lesson_metadata=dto.lesson_metadata,
            )
            lesson_data["status"] = initial_status
            lesson_data["status_history"] = [status_event(
                initial_status, "student", actor_user_id=token.user_id,
                meta=None if confirmed else {"request": True},
            )]
            lesson_data = serialize_for_db("lessons", lesson_data)
            try:
                lesson = await self._db.create("lessons", lesson_data)
            except Exception as e:
                if is_unique_violation(e):
                    raise ConflictError("Lesson already exists")
                raise

            # Снапшот цены связи на день урока — в строку участия.
            # Связь здесь обязательна (проверена выше), снапшот всегда пишется.
            participant_data = {
                "lesson_id": lesson["id"],
                "student_id": student_id,
                "participant_settings": build_price_snapshot(
                    config["hourly_rate"], config["discount"], config["id"]
                ),
            }
            participant_data = serialize_for_db("lesson_participants", participant_data)
            try:
                participant = await self._db.create("lesson_participants", participant_data)
            except Exception as e:
                # Компенсация: не оставляем сироту-урок без участника,
                # т.к. инфраструктура не даёт атомарных транзакций.
                try:
                    await self._db.delete("lessons", lesson["id"])
                except Exception:
                    pass
                if is_unique_violation(e):
                    raise ConflictError("Student is already a participant")
                raise

            student_name = await get_user_name(self._db, token.user_id)
            if confirmed:
                await _notify_tutor(
                    self._db, tutor_id, "lesson_booked",
                    f"Ученик {student_name} записался на урок {format_lesson_time(start_time)}",
                )
            else:
                await _notify_tutor(
                    self._db, tutor_id, "lesson_requested",
                    f"Ученик {student_name} просит подтвердить урок {format_lesson_time(start_time)}",
                )
            return StudentCreateLessonResponse(
                lesson_id=lesson["id"],
                tutor_id=tutor_id,
                start_time=str(lesson["start_time"]),
                end_time=str(lesson["end_time"]),
                is_group=lesson["is_group"],
                created_by_id=lesson["created_by_id"],
                participant_id=participant["id"],
                lesson_links=lesson_links,
                status=lesson.get("status") or "SCHEDULED",
            )


@register_scenario("student_join_lesson", dto=StudentJoinLessonDTO, response=StudentJoinLessonResponse)
@tracked_scenario("student_join_lesson")
class StudentJoinLessonScenario(BaseScenario):
    async def execute(self, dto: StudentJoinLessonDTO) -> StudentJoinLessonResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        lesson_rows = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lesson_rows:
            raise NotFoundError("Lesson not found")

        lesson = lesson_rows[0]
        now = utc_now()
        from app.utils.participants import validate_lesson_not_ended
        validate_lesson_not_ended(_to_dt(lesson["end_time"]), now)

        # Ленивый синк + запрет входа в завершённые уроки.
        new_status = resolve_lesson_status(
            lesson.get("status"), _to_dt(lesson["start_time"]), _to_dt(lesson["end_time"]), now
        )
        if new_status is not None and new_status != lesson.get("status"):
            await self._db.update("lessons", lesson["id"], {"status": new_status})
            lesson = {**lesson, "status": new_status}
        if lesson.get("status") in TERMINAL_LESSON_STATUSES:
            raise ForbiddenError(f"Cannot join lesson in status {lesson.get('status')}")

        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid AND status = :active',
            {"sid": student_id, "tid": lesson["tutor_id"], "active": "ACTIVE"},
        )
        if not configs:
            raise ForbiddenError("You don't have a configuration with this tutor")
        config = configs[0]
        if not config["allow_self_booking"]:
            raise ForbiddenError("Self-booking is not allowed for you")

        # Режим самозаписи репетитора (как в доступных слотах):
        # NO — только белый список.
        tutor_settings_rows = await self._db.query(
            'SELECT self_booking_mode, self_booking_whitelist FROM "tutor_settings" WHERE tutor_id = :tid',
            {"tid": lesson["tutor_id"]},
        )
        if tutor_settings_rows:
            mode = tutor_settings_rows[0].get("self_booking_mode", "YES")
            if mode == "NO":
                whitelist = parse_int_list(tutor_settings_rows[0].get("self_booking_whitelist"))
                if student_id not in whitelist:
                    raise ForbiddenError("Self-booking is not available for you")

        existing = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
            {"lid": dto.lesson_id, "sid": student_id},
        )
        if existing:
            # Возврат на урок: была отменённая запись — гасим отмену,
            # снапшот и paid не трогаем. Активная — идемпотентный возврат.
            if is_cancelled_row(existing[0]):
                settings = parse_row("lesson_participants", existing[0]).get("participant_settings") or {}
                settings.pop("cancelled", None)
                await self._db.update(
                    "lesson_participants",
                    existing[0]["id"],
                    serialize_for_db("lesson_participants", {"participant_settings": settings}),
                )
                await _notify_join(self._db, dto.lesson_id, token.user_id)
            return StudentJoinLessonResponse(participant_id=existing[0]["id"])

        # Новое вступление ученика: только групповые уроки, доступные
        # по ограничениям репетитора. Индивидуальные — через слоты
        # (student_create_lesson); репетитор добавляет напрямую.
        if not lesson.get("is_group"):
            raise ForbiddenError("Only group lessons can be joined directly")
        lesson_start = _to_dt(lesson["start_time"])
        if lesson_start > now:
            validate_booking_lead_time(now, lesson_start, config.get("booking_lead_time_hours", 0))

        # Снапшот цены связи на день урока — в строку участия.
        participant_data = {
            "lesson_id": dto.lesson_id,
            "student_id": student_id,
            "participant_settings": build_price_snapshot(
                config["hourly_rate"], config["discount"], config["id"]
            ),
        }
        participant_data = serialize_for_db("lesson_participants", participant_data)
        try:
            participant = await self._db.create("lesson_participants", participant_data)
        except Exception as e:
            if is_unique_violation(e):
                # Гонка: кто-то создал между check и create — возвращаем существующего.
                again = await self._db.query(
                    'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
                    {"lid": dto.lesson_id, "sid": student_id},
                )
                if again:
                    if is_cancelled_row(again[0]):
                        settings = parse_row("lesson_participants", again[0]).get("participant_settings") or {}
                        settings.pop("cancelled", None)
                        await self._db.update(
                            "lesson_participants",
                            again[0]["id"],
                            serialize_for_db("lesson_participants", {"participant_settings": settings}),
                        )
                    return StudentJoinLessonResponse(participant_id=again[0]["id"])
                raise ConflictError("Student is already a participant")
            raise

        await _notify_join(self._db, dto.lesson_id, token.user_id)

        return StudentJoinLessonResponse(participant_id=participant["id"])


@register_scenario("student_leave_lesson", dto=StudentLeaveLessonDTO, response=StudentLeaveLessonResponse)
@tracked_scenario("student_leave_lesson")
class StudentLeaveLessonScenario(BaseScenario):
    async def execute(self, dto: StudentLeaveLessonDTO) -> StudentLeaveLessonResponse:
        token = extract_token_info(dto.access_token)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not students:
            raise NotFoundError("Student profile not found")
        student_id = students[0]["id"]

        participants = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
            {"lid": dto.lesson_id, "sid": student_id},
        )
        if not participants:
            raise NotFoundError("Not a participant of this lesson")

        lesson_rows = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lesson_rows:
            raise NotFoundError("Lesson not found")
        lesson = lesson_rows[0]
        # Повторный выход — идемпотентный ok (урок к этому моменту уже может быть отменён).
        if is_cancelled_row(participants[0]):
            return StudentLeaveLessonResponse(ok=True)
        now = utc_now()
        stored = lesson.get("status") or "SCHEDULED"
        # Эффективный статус в памяти (урок из прошлого считаем
        # завершённым): историю задним числом не переписываем.
        effective = resolve_lesson_status(
            stored, _to_dt(lesson["start_time"]), _to_dt(lesson["end_time"]), now
        ) or stored
        validate_lesson_not_terminal(effective)
        is_request = effective == "PENDING"
        if not is_request:
            # Дедлайн отмены по связи (репетитор задаёт время для ученика).
            # Заявку, которую репетитор ещё не подтвердил, можно отозвать всегда.
            configs = await self._db.query(
                'SELECT cancellation_lead_time_hours FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid',
                {"sid": student_id, "tid": lesson["tutor_id"]},
            )
            lead_hours = configs[0].get("cancellation_lead_time_hours", 0) if configs else 0
            validate_cancellation_deadline(now, _to_dt(lesson["start_time"]), lead_hours, student_id)

        # Выход помечает запись, а не удаляет: история для статистики.
        settings = parse_row("lesson_participants", participants[0]).get("participant_settings") or {}
        settings["cancelled"] = build_cancellation(
            "student", now, actor_user_id=token.user_id, reason=dto.reason,
        )
        await self._db.update(
            "lesson_participants",
            participants[0]["id"],
            serialize_for_db("lesson_participants", {"participant_settings": settings}),
        )

        # Индивидуальный урок без оставшихся учеников отменён учеником целиком:
        # время репетитора освобождается, событие попадает в историю отмен.
        others = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id != :sid',
            {"lid": dto.lesson_id, "sid": student_id},
        )
        active_left = [p for p in others if not is_cancelled_row(p)]
        if not lesson.get("is_group") or not active_left:
            history = parse_row("lessons", lesson).get("status_history")
            event = status_event(
                "CANCELLED", "student", actor_user_id=token.user_id, reason=dto.reason,
                meta={"withdrawn_request": True} if is_request else None,
            )
            await self._db.update("lessons", dto.lesson_id, serialize_for_db("lessons", {
                "status": "CANCELLED",
                "status_history": with_status_event(history, event),
            }))

        student_name = await get_user_name(self._db, token.user_id)
        action = "отозвал заявку на урок" if is_request else "отменил урок"
        reason = f". Причина: {dto.reason.strip()}" if dto.reason and dto.reason.strip() else ""
        await _notify_tutor(
            self._db, lesson["tutor_id"], "lesson_left",
            f"Ученик {student_name} {action} {format_lesson_time(lesson['start_time'])}{reason}",
        )
        return StudentLeaveLessonResponse(ok=True)


def _to_dt(value) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return to_utc_naive(value)
    if isinstance(value, str):
        return parse_iso_datetime(value.replace(" ", "T"), "datetime")
    return value
