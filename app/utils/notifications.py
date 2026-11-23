import datetime

from app.utils.json_codec import serialize_for_db
from app.utils.participants import is_cancelled_row


def format_lesson_time(value) -> str:
    dt = value
    if isinstance(dt, str):
        try:
            from app.utils.safe_parse import parse_iso_datetime

            dt = parse_iso_datetime(dt.replace(" ", "T"), "datetime")
        except Exception:
            return str(value)
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    return str(value)


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
