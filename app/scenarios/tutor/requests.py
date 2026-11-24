"""Заявки учеников на уроки: подтверждение и отклонение репетитором.

Заявка (статус PENDING) время не занимает: на одно время может быть несколько
заявок разных учеников. Подтверждение проверяет занятость и автоматически
отклоняет пересекающиеся заявки (событие от имени системы). Заявку без ответа
к началу урока отклоняет фоновая задача (app/scenarios/system/lesson_upkeep.py).
"""
import datetime

from pydantic import BaseModel, Field
from core import BaseScenario, ConflictError, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.dto import BaseDTO
from core.utils.security import extract_token_info

from app.utils.clock import to_utc_naive, utc_now
from app.utils.json_codec import parse_row, serialize_for_db
from app.utils.lessons import check_lesson_overlap, status_event, tutor_schedule_lock, with_status_event
from app.utils.notifications import format_lesson_time, get_user_name, notify_participants


class TutorDecideLessonDTO(BaseDTO):
    lesson_id: int = 0
    reason: str | None = Field(default=None, max_length=500)


class TutorDecideLessonResponse(BaseModel):
    lesson_id: int
    status: str
    rejected_overlapping: list[int] = []


def _dt(value) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return to_utc_naive(value)
    return datetime.datetime.fromisoformat(str(value).replace(" ", "T"))


async def _own_pending(db, user_id: int, lesson_id: int) -> tuple[int, dict]:
    tutors = await db.query('SELECT id FROM "tutors" WHERE user_id = :uid', {"uid": user_id})
    if not tutors:
        raise NotFoundError("Tutor not found")
    tutor_id = tutors[0]["id"]
    rows = await db.query(
        'SELECT * FROM "lessons" WHERE id = :lid AND tutor_id = :tid',
        {"lid": lesson_id, "tid": tutor_id},
    )
    if not rows:
        raise NotFoundError("Lesson not found or access denied")
    lesson = rows[0]
    if (lesson.get("status") or "SCHEDULED") != "PENDING":
        raise ValidationError("Lesson is not awaiting confirmation")
    if _dt(lesson["start_time"]) <= utc_now():
        raise ValidationError("Lesson request has expired")
    return tutor_id, lesson


async def _set_status(db, lesson: dict, status: str, event: dict) -> None:
    history = parse_row("lessons", lesson).get("status_history")
    await db.update("lessons", lesson["id"], serialize_for_db("lessons", {
        "status": status,
        "status_history": with_status_event(history, event),
    }))


@register_scenario("tutor_confirm_lesson", dto=TutorDecideLessonDTO, response=TutorDecideLessonResponse)
@tracked_scenario("tutor_confirm_lesson")
class TutorConfirmLessonScenario(BaseScenario):
    async def execute(self, dto: TutorDecideLessonDTO) -> TutorDecideLessonResponse:
        token = extract_token_info(dto.access_token)
        tutor_id, _ = await _own_pending(self._db, token.user_id, dto.lesson_id)
        async with (await tutor_schedule_lock(tutor_id)):
            # Повторное чтение под локом: заявку могли успеть решить или отозвать.
            tutor_id, lesson = await _own_pending(self._db, token.user_id, dto.lesson_id)
            start, end = _dt(lesson["start_time"]), _dt(lesson["end_time"])
            busy = await self._db.query(
                'SELECT id FROM "lessons" WHERE tutor_id = :tid AND start_time < :et AND end_time > :st '
                "AND id != :lid AND (status IS NULL OR status NOT IN ('CANCELLED', 'REJECTED', 'PENDING'))",
                {"tid": tutor_id, "et": end, "st": start, "lid": lesson["id"]},
            )
            try:
                check_lesson_overlap(busy)
            except ConflictError:
                raise ConflictError("Time is already taken by another lesson")
            await _set_status(self._db, lesson, "SCHEDULED", status_event(
                "SCHEDULED", "tutor", actor_user_id=token.user_id, reason=dto.reason,
                meta={"confirmed_request": True},
            ))

            # Пересекающиеся заявки других учеников больше не могут быть приняты.
            competing = await self._db.query(
                'SELECT * FROM "lessons" WHERE tutor_id = :tid AND status = :pending '
                'AND start_time < :et AND end_time > :st AND id != :lid',
                {"tid": tutor_id, "pending": "PENDING", "et": end, "st": start, "lid": lesson["id"]},
            )
            for other in competing:
                await _set_status(self._db, other, "REJECTED", status_event(
                    "REJECTED", "system", reason="Время занято подтверждённым уроком",
                    meta={"superseded_by": lesson["id"]},
                ))
                await notify_participants(
                    self._db, other["id"], "lesson_rejected",
                    f"Заявка на урок {format_lesson_time(other['start_time'])} отклонена: "
                    "это время уже занято другим уроком",
                )

        tutor_name = await get_user_name(self._db, token.user_id)
        await notify_participants(
            self._db, lesson["id"], "lesson_confirmed",
            f"Репетитор {tutor_name} подтвердил урок {format_lesson_time(lesson['start_time'])}",
        )
        return TutorDecideLessonResponse(
            lesson_id=lesson["id"], status="SCHEDULED",
            rejected_overlapping=[o["id"] for o in competing],
        )


@register_scenario("tutor_reject_lesson", dto=TutorDecideLessonDTO, response=TutorDecideLessonResponse)
@tracked_scenario("tutor_reject_lesson")
class TutorRejectLessonScenario(BaseScenario):
    async def execute(self, dto: TutorDecideLessonDTO) -> TutorDecideLessonResponse:
        token = extract_token_info(dto.access_token)
        tutor_id, _ = await _own_pending(self._db, token.user_id, dto.lesson_id)
        async with (await tutor_schedule_lock(tutor_id)):
            tutor_id, lesson = await _own_pending(self._db, token.user_id, dto.lesson_id)
            await _set_status(self._db, lesson, "REJECTED", status_event(
                "REJECTED", "tutor", actor_user_id=token.user_id, reason=dto.reason,
            ))
        tutor_name = await get_user_name(self._db, token.user_id)
        reason = f". Причина: {dto.reason.strip()}" if dto.reason and dto.reason.strip() else ""
        await notify_participants(
            self._db, lesson["id"], "lesson_rejected",
            f"Репетитор {tutor_name} отклонил заявку на урок {format_lesson_time(lesson['start_time'])}{reason}",
        )
        return TutorDecideLessonResponse(lesson_id=lesson["id"], status="REJECTED")
