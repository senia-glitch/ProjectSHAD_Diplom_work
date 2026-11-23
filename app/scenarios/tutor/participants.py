from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ConflictError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO
from app.utils.json_codec import serialize_for_db, parse_row
from app.core.exceptions import ForbiddenError
from app.utils.db_errors import is_unique_violation
from app.utils.participants import (
    validate_is_lesson_owner,
    validate_not_already_participant,
    validate_not_cancelled,
    validate_lesson_not_terminal,
    build_price_snapshot,
    build_cancellation,
    is_cancelled_row,
)
from app.utils.notifications import notify_user, get_user_name, format_lesson_time


class TutorGetParticipantsDTO(BaseDTO):
    lesson_id: int


class TutorParticipantItem(BaseModel):
    participant_id: int
    student_id: int
    student_user_id: int


class TutorGetParticipantsResponse(BaseModel):
    participants: list[TutorParticipantItem]


@register_scenario("tutor_get_participants")
@tracked_scenario("tutor_get_participants")
class TutorGetParticipantsScenario(BaseScenario):
    async def execute(self, dto: TutorGetParticipantsDTO) -> TutorGetParticipantsResponse:
        token = extract_token_info(dto.access_token)
        user_id = token.user_id

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        lessons = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lessons:
            raise NotFoundError(f"Lesson {dto.lesson_id} not found")
        lesson = lessons[0]

        validate_is_lesson_owner(lesson["tutor_id"], tutor_id)

        participants = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid',
            {"lid": dto.lesson_id},
        )

        result = []
        for p in participants:
            # Отменённые записи в панели участников не показываем.
            if is_cancelled_row(p):
                continue
            students = await self._db.query(
                'SELECT user_id FROM "students" WHERE id = :sid',
                {"sid": p["student_id"]},
            )
            result.append(TutorParticipantItem(
                participant_id=p["id"],
                student_id=p["student_id"],
                student_user_id=students[0]["user_id"] if students else 0,
            ))

        return TutorGetParticipantsResponse(participants=result)


class TutorAddParticipantDTO(BaseDTO):
    lesson_id: int | None = None
    student_user_id: int


class TutorAddParticipantResponse(BaseModel):
    participant_id: int
    lesson_id: int
    student_id: int


@register_scenario("tutor_add_participant")
@tracked_scenario("tutor_add_participant")
class TutorAddParticipantScenario(BaseScenario):
    async def execute(self, dto: TutorAddParticipantDTO) -> TutorAddParticipantResponse:
        token = extract_token_info(dto.access_token)
        user_id = token.user_id

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        lessons = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lessons:
            raise NotFoundError(f"Lesson {dto.lesson_id} not found")
        lesson = lessons[0]

        validate_is_lesson_owner(lesson["tutor_id"], tutor_id)
        validate_lesson_not_terminal(lesson.get("status"))

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": dto.student_user_id},
        )
        if not students:
            raise NotFoundError("Student not found")
        student_id = students[0]["id"]

        if dto.lesson_id is None:
            raise ValidationError("lesson_id is required")

        existing = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
            {"lid": dto.lesson_id, "sid": student_id},
        )
        if existing and is_cancelled_row(existing[0]):
            # Возврат снятого ученика: гасим отмену, снапшот и paid не трогаем.
            settings = parse_row("lesson_participants", existing[0]).get("participant_settings") or {}
            settings.pop("cancelled", None)
            await self._db.update(
                "lesson_participants",
                existing[0]["id"],
                serialize_for_db("lesson_participants", {"participant_settings": settings}),
            )
            await _notify_participant_added(self._db, user_id, dto.student_user_id, lesson)
            return TutorAddParticipantResponse(
                participant_id=existing[0]["id"],
                lesson_id=dto.lesson_id,
                student_id=student_id,
            )
        validate_not_already_participant(existing)

        # Снапшот цены: фиксируем ставку/скидку связи на день урока.
        # Связь обязательна: репетитор может добавлять только своих учеников.
        configs = await self._db.query(
            'SELECT * FROM "configurations" WHERE student_id = :sid AND tutor_id = :tid',
            {"sid": student_id, "tid": tutor_id},
        )
        if not configs:
            raise ForbiddenError("Student has no configuration with you")
        participant_data = {
            "lesson_id": dto.lesson_id,
            "student_id": student_id,
        }
        if configs:
            participant_data["participant_settings"] = build_price_snapshot(
                configs[0]["hourly_rate"], configs[0]["discount"], configs[0]["id"]
            )
        participant_data = serialize_for_db("lesson_participants", participant_data)
        try:
            participant = await self._db.create("lesson_participants", participant_data)
        except Exception as e:
            if is_unique_violation(e):
                # Гонка: строка появилась между check и create.
                again = await self._db.query(
                    'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
                    {"lid": dto.lesson_id, "sid": student_id},
                )
                if again and is_cancelled_row(again[0]):
                    settings = parse_row("lesson_participants", again[0]).get("participant_settings") or {}
                    settings.pop("cancelled", None)
                    await self._db.update(
                        "lesson_participants",
                        again[0]["id"],
                        serialize_for_db("lesson_participants", {"participant_settings": settings}),
                    )
                    await _notify_participant_added(self._db, user_id, dto.student_user_id, lesson)
                    return TutorAddParticipantResponse(
                        participant_id=again[0]["id"],
                        lesson_id=dto.lesson_id,
                        student_id=student_id,
                    )
                raise ConflictError("Student is already a participant")
            raise

        await _notify_participant_added(self._db, user_id, dto.student_user_id, lesson)

        return TutorAddParticipantResponse(
            participant_id=participant["id"],
            lesson_id=dto.lesson_id,
            student_id=student_id,
        )


class TutorRemoveParticipantDTO(BaseDTO):
    lesson_id: int
    student_user_id: int


class TutorRemoveParticipantResponse(BaseModel):
    ok: bool


@register_scenario("tutor_remove_participant")
@tracked_scenario("tutor_remove_participant")
class TutorRemoveParticipantScenario(BaseScenario):
    async def execute(self, dto: TutorRemoveParticipantDTO) -> TutorRemoveParticipantResponse:
        token = extract_token_info(dto.access_token)
        user_id = token.user_id

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        lessons = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lessons:
            raise NotFoundError(f"Lesson {dto.lesson_id} not found")
        lesson = lessons[0]

        validate_is_lesson_owner(lesson["tutor_id"], tutor_id)
        validate_lesson_not_terminal(lesson.get("status"))

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": dto.student_user_id},
        )
        if not students:
            raise NotFoundError("Student not found")
        student_id = students[0]["id"]

        participants = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
            {"lid": dto.lesson_id, "sid": student_id},
        )
        if not participants:
            raise NotFoundError("Participant not found")

        # Снятие помечает запись репетитором, а не удаляет.
        # Уже отменённая — идемпотентный ok.
        if not is_cancelled_row(participants[0]):
            settings = parse_row("lesson_participants", participants[0]).get("participant_settings") or {}
            settings["cancelled"] = build_cancellation("tutor")
            await self._db.update(
                "lesson_participants",
                participants[0]["id"],
                serialize_for_db("lesson_participants", {"participant_settings": settings}),
            )
            await _notify_participant_removed(self._db, user_id, dto.student_user_id, lesson)
        return TutorRemoveParticipantResponse(ok=True)


class TutorSetPaymentDTO(BaseDTO):
    lesson_id: int | None = None
    student_user_id: int | None = None
    paid: bool


class TutorSetPaymentResponse(BaseModel):
    lesson_id: int
    student_id: int
    paid: bool


@register_scenario("tutor_set_payment")
@tracked_scenario("tutor_set_payment")
class TutorSetPaymentScenario(BaseScenario):
    async def execute(self, dto: TutorSetPaymentDTO) -> TutorSetPaymentResponse:
        token = extract_token_info(dto.access_token)
        user_id = token.user_id

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        lessons = await self._db.query(
            'SELECT * FROM "lessons" WHERE id = :lid',
            {"lid": dto.lesson_id},
        )
        if not lessons:
            raise NotFoundError(f"Lesson {dto.lesson_id} not found")
        lesson = lessons[0]

        validate_is_lesson_owner(lesson["tutor_id"], tutor_id)

        students = await self._db.query(
            'SELECT id FROM "students" WHERE user_id = :uid',
            {"uid": dto.student_user_id},
        )
        if not students:
            raise NotFoundError("Student not found")
        student_id = students[0]["id"]

        participants = await self._db.query(
            'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid AND student_id = :sid',
            {"lid": dto.lesson_id, "sid": student_id},
        )
        if not participants:
            raise NotFoundError("Participant not found")

        # Оплату отменённой записи не меняем.
        validate_not_cancelled(participants[0])

        # Флаг кладём рядом с остальными настройками участия (там же снапшот
        # цены), ничего не затирая. Отсутствие флага = "нет".
        settings = parse_row("lesson_participants", participants[0]).get("participant_settings") or {}
        settings["paid"] = bool(dto.paid)
        await self._db.update(
            "lesson_participants",
            participants[0]["id"],
            serialize_for_db("lesson_participants", {"participant_settings": settings}),
        )
        await notify_user(
            self._db, dto.student_user_id, "payment_updated",
            f"Оплата урока {format_lesson_time(lesson['start_time'])} отмечена: {'оплачено' if dto.paid else 'не оплачено'}",
        )
        return TutorSetPaymentResponse(
            lesson_id=dto.lesson_id,
            student_id=student_id,
            paid=bool(dto.paid),
        )


async def _notify_participant_added(db, tutor_user_id: int, student_user_id: int, lesson: dict) -> None:
    tutor_name = await get_user_name(db, tutor_user_id)
    await notify_user(
        db, student_user_id, "lesson_added",
        f"Репетитор {tutor_name} добавил вас в урок {format_lesson_time(lesson['start_time'])}",
    )


async def _notify_participant_removed(db, tutor_user_id: int, student_user_id: int, lesson: dict) -> None:
    tutor_name = await get_user_name(db, tutor_user_id)
    await notify_user(
        db, student_user_id, "lesson_removed",
        f"Репетитор {tutor_name} убрал вас из урока {format_lesson_time(lesson['start_time'])}",
    )
