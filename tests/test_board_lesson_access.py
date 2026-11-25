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


# ---------- доска урока (без кода) ----------
from app.scenarios.boards.boards import AdmitDTO, AdmitToBoard, LessonBoard, LessonBoardDTO, _lesson_member, user_key


class LessonStub:
    """Урок 3 репетитора user 5; записан user 6, user 7 отменил; доска урока создаётся при первом открытии."""

    def __init__(self):
        self.boards = {}

    async def query(self, sql, params, **kw):
        if 'FROM lessons l JOIN tutors t' in sql:
            if params['lid'] != 3:
                return []
            row = {'tutor_user_id': 5, 'id': 3}
            if 'l.start_time' in sql:
                import datetime
                row['start_time'] = datetime.datetime(2030, 1, 10, 10, 0)
            return [row]
        if 'FROM lesson_participants' in sql:
            return {6: [{'participant_settings': '{}'}],
                    7: [{'participant_settings': '{"cancelled": {"by": "student"}}'}]}.get(params['uid'], [])
        if sql.startswith('SELECT id, title FROM boards WHERE lesson_id'):
            b = self.boards.get(params['lid'])
            return [b] if b else []
        if sql.startswith('INSERT INTO boards'):
            self.boards.setdefault(params['lid'], {'id': params['id'], 'title': params['title'], 'creator': params['creator']})
            return []
        if 'FROM boards b' in sql and 'LEFT JOIN board_members' in sql:
            return [{'title': 'Урок', 'code_lookup': None, 'creator_key': user_key(5), 'lesson_id': 3, 'banned': None}]
        return []


def test_lesson_member_rules():
    db = LessonStub()
    assert run(_lesson_member(db, 3, 5)) and run(_lesson_member(db, 3, 6))
    assert not run(_lesson_member(db, 3, 7)) and not run(_lesson_member(db, 3, 99))


def test_lesson_board_created_once_with_tutor_as_creator():
    db = LessonStub()
    first = run(LessonBoard(db=db).execute(LessonBoardDTO(lesson_id=3, user_id=6)))
    again = run(LessonBoard(db=db).execute(LessonBoardDTO(lesson_id=3, user_id=5)))
    assert first.id == again.id and first.title.startswith('Урок 10.01.2030')
    assert db.boards[3]['creator'] == user_key(5)


def test_lesson_board_admit_without_code():
    db = LessonStub()
    ok = run(AdmitToBoard(db=db).execute(AdmitDTO(board_id=BOARD, author=user_key(6), user_id=6)))
    assert ok.granted and ok.via == 'lesson'
    denied = run(AdmitToBoard(db=db).execute(AdmitDTO(board_id=BOARD, author=user_key(99), user_id=99, code='ANYCODE1')))
    assert not denied.granted and denied.lesson_only
