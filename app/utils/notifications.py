import datetime
import re

from app.utils.clock import to_local
from app.utils.json_codec import serialize_for_db
from app.utils.participants import is_cancelled_row


TIME_MARK = re.compile(r"⟦t:([0-9T:\-. ]+)⟧")


def format_lesson_time(value) -> str:
    """Метка момента (наивный UTC) для текста уведомления.

    Конкретное «ДД.ММ.ГГГГ ЧЧ:ММ» подставляет notify_user в личном поясе
    получателя: у репетитора и ученика из разных поясов время своё.
    """
    dt = value
    if isinstance(dt, str):
        try:
            from app.utils.safe_parse import parse_iso_datetime

            dt = parse_iso_datetime(dt.replace(" ", "T"), "datetime")
        except Exception:
            return str(value)
    if isinstance(dt, datetime.datetime):
        return "⟦t:" + dt.replace(microsecond=0).isoformat() + "⟧"
    return str(value)


def render_times(text: str, offset_hours) -> str:
    """Подставить метки времени в поясе получателя."""
    def repl(match):
        try:
            moment = datetime.datetime.fromisoformat(match.group(1))
        except ValueError:
            return match.group(1)
        return to_local(moment, offset_hours).strftime("%d.%m.%Y %H:%M")
    return TIME_MARK.sub(repl, text)


async def user_offset(db, user_id: int) -> int:
    """Личный пояс пользователя (часы от UTC); администратор — UTC."""
    rows = await db.query(
        'SELECT ts.timezone_offset FROM "tutors" t JOIN "tutor_settings" ts ON ts.tutor_id = t.id '
        'WHERE t.user_id = :uid',
        {"uid": user_id},
    )
    if not rows:
        rows = await db.query(
            'SELECT ss.timezone_offset FROM "students" s JOIN "student_settings" ss ON ss.student_id = s.id '
            'WHERE s.user_id = :uid',
            {"uid": user_id},
        )
    return int((rows[0].get("timezone_offset") if rows else 0) or 0)


async def get_user_name(db, user_id: int) -> str:
    rows = await db.query(
        'SELECT full_name FROM "users" WHERE id = :uid',
        {"uid": user_id},
    )
    return rows[0]["full_name"] if rows else "Пользователь"


async def get_tutor_user_id(db, tutor_id: int):
    rows = await db.query(
        'SELECT user_id FROM "tutors" WHERE id = :tid',
        {"tid": tutor_id},
    )
    return rows[0]["user_id"] if rows else None


async def get_student_user_id(db, student_id: int):
    rows = await db.query(
        'SELECT user_id FROM "students" WHERE id = :sid',
        {"sid": student_id},
    )
    return rows[0]["user_id"] if rows else None


async def notify_user(db, user_id: int, ntype: str, text: str) -> None:
    try:
        if TIME_MARK.search(text):
            try:
                offset = await user_offset(db, user_id)
            except Exception:
                offset = 0  # пояс неизвестен — UTC, но уведомление не теряем
            text = render_times(text, offset)
        data = serialize_for_db("notifications", {
            "user_id": user_id,
            "type": ntype,
            "payload": {"text": text},
        })
        await db.create("notifications", data)
    except Exception:
        pass


async def notify_participants(db, lesson_id: int, ntype: str, text: str) -> None:
    participants = await db.query(
        'SELECT * FROM "lesson_participants" WHERE lesson_id = :lid',
        {"lid": lesson_id},
    )
    for p in participants:
        if is_cancelled_row(p):
            continue
        students = await db.query(
            'SELECT user_id FROM "students" WHERE id = :sid',
            {"sid": p["student_id"]},
        )
        if students:
            await notify_user(db, students[0]["user_id"], ntype, text)
