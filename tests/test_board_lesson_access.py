# Доска, прикреплённая к уроку: репетитор и записанные ученики входят без кода.
# Запуск: pytest tests/test_board_lesson_access.py -q
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scenarios.boards.boards import _lesson_access

BOARD = 'GMDPJyXMNk2-P59nZCDeZw'


class Stub:
    """Урок 2 с доской: репетитор user 5, ученик user 6 записан, ученик user 7 отменил запись."""

    def __init__(self, lessons=True):
        self.lessons = lessons
        self.calls = []

    async def query(self, sql, params, **kw):
        self.calls.append((sql, params))
        if 'FROM lessons l' in sql:
            assert params['needle'] == f'/boards/{BOARD}"' and params['bid'] == BOARD
            return [{'id': 2, 'tutor_user_id': 5}] if self.lessons else []
        if 'FROM lesson_participants' in sql:
            if params['uid'] == 6:
                return [{'participant_settings': '{}'}]
            if params['uid'] == 7:
                return [{'participant_settings': '{"cancelled": {"by": "student", "at": "2030-01-01T10:00:00"}}'}]
            return []
        return []


def run(coro):
    return asyncio.run(coro)


def test_tutor_and_enrolled_student_enter_without_code():
    assert run(_lesson_access(Stub(), BOARD, 5)) is True
    assert run(_lesson_access(Stub(), BOARD, 6)) is True


def test_outsiders_and_cancelled_students_need_code():
    assert run(_lesson_access(Stub(), BOARD, 7)) is False
    assert run(_lesson_access(Stub(), BOARD, 99)) is False
    # Урок не идёт (или доска не прикреплена к уроку её владельца) — только по коду.
    assert run(_lesson_access(Stub(lessons=False), BOARD, 5)) is False


def test_query_limits_to_owner_lessons_in_time_window():
    stub = Stub()
    run(_lesson_access(stub, BOARD, 5))
    sql, params = stub.calls[0]
    assert 'b.owner_id = t.user_id' in sql
    assert params['latest_start'] > params['earliest_end']
