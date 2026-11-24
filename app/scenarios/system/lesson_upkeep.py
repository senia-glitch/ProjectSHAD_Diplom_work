"""Фоновое обслуживание уроков (внутренний сценарий, вызывается циклом в app/main.py).

1. Заявка (PENDING), на которую репетитор не ответил к началу урока, отклоняется системой.
2. Начавшийся урок, пришедшийся на отпуск/болезнь репетитора, закрывается системой
   (SYSTEM_FINISHED): репетитор сам себе хозяин, платформа фиксирует, что урок не
   состоялся из-за его отсутствия. В оплатах и статистике такой урок не учитывается.
"""
import datetime

from pydantic import BaseModel
from core import BaseScenario, register_scenario
from core.dto import BaseDTO

from app.utils.clock import to_utc_naive, utc_now
from app.utils.json_codec import parse_row, serialize_for_db
from app.utils.lessons import status_event, with_status_event
from app.utils.notifications import format_lesson_time, get_tutor_user_id, notify_participants, notify_user

ABSENCE_LABELS = {"VACATION": "в отпуске", "SICK": "болеет"}


class LessonUpkeepDTO(BaseDTO):
    pass


class LessonUpkeepResponse(BaseModel):
    expired_requests: int = 0
    system_finished: int = 0


def _dt(value) -> datetime.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return to_utc_naive(value)
    return datetime.datetime.fromisoformat(str(value).replace(" ", "T"))


async def _close(db, lesson: dict, status: str, event: dict) -> None:
    history = parse_row("lessons", lesson).get("status_history")
    await db.update("lessons", lesson["id"], serialize_for_db("lessons", {
        "status": status,
        "status_history": with_status_event(history, event),
    }))


@register_scenario("lesson_upkeep", dto=LessonUpkeepDTO, response=LessonUpkeepResponse)
class LessonUpkeepScenario(BaseScenario):
    async def execute(self, dto: LessonUpkeepDTO) -> LessonUpkeepResponse:
        now = utc_now()
        result = LessonUpkeepResponse()

        expired = await self._db.query(
            'SELECT * FROM "lessons" WHERE status = :pending AND start_time <= :now',
            {"pending": "PENDING", "now": now},
        )
        for lesson in expired:
            await _close(self._db, lesson, "REJECTED", status_event(
                "REJECTED", "system", reason="Репетитор не ответил на заявку до начала урока",
                meta={"expired_request": True},
            ))
            await notify_participants(
                self._db, lesson["id"], "lesson_rejected",
                f"Заявка на урок {format_lesson_time(lesson['start_time'])} отклонена: "
                "репетитор не ответил до начала урока",
            )
            result.expired_requests += 1

        absent = await self._db.query(
            'SELECT tutor_id, absence_status, absence_from, absence_to FROM "tutor_settings" '
            'WHERE absence_status IS NOT NULL AND absence_from IS NOT NULL AND absence_to IS NOT NULL '
            'AND absence_from <= :now',
            {"now": now},
        )
        for period in absent:
            start, end = _dt(period["absence_from"]), _dt(period["absence_to"])
            # Начавшиеся уроки, чьё начало пришлось на период отсутствия.
            lessons = await self._db.query(
                'SELECT * FROM "lessons" WHERE tutor_id = :tid AND start_time <= :now '
                'AND start_time >= :ps AND start_time < :pe '
                "AND (status IS NULL OR status IN ('SCHEDULED', 'ONGOING'))",
                {"tid": period["tutor_id"], "now": now, "ps": start, "pe": end},
            )
            label = ABSENCE_LABELS.get(period["absence_status"], "отсутствует")
            for lesson in lessons:
                await _close(self._db, lesson, "SYSTEM_FINISHED", status_event(
                    "SYSTEM_FINISHED", "system", reason=f"Репетитор {label}",
                    meta={"absence": {
                        "status": period["absence_status"],
                        "from": start.isoformat(), "to": end.isoformat(),
                    }},
                ))
                text = (f"Урок {format_lesson_time(lesson['start_time'])} завершён системой: "
                        f"репетитор {label}")
                await notify_participants(self._db, lesson["id"], "lesson_system_finished", text)
                tutor_user_id = await get_tutor_user_id(self._db, period["tutor_id"])
                if tutor_user_id is not None:
                    await notify_user(self._db, tutor_user_id, "lesson_system_finished", text)
                result.system_finished += 1
        return result
