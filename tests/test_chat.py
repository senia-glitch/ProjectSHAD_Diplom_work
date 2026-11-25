# Личный чат: пишут по действующей связи, без связи — только история, лимит хранения.
# Запуск: pytest tests/test_chat.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import NotFoundError

from app.core.exceptions import ForbiddenError
from app.scenarios.chat import messages as chat

TUTOR, STUDENT, STRANGER = 5, 6, 9


class Stub:
    def __init__(self, link_status='ACTIVE'):
        self.link_status = link_status
        self.rows = {}
        self.seq = 0

    async def query(self, sql, params, **kw):
        if 'FROM configurations c' in sql:
            if self.link_status and params['me'] in (TUTOR, STUDENT):
                return [{'tutor_uid': TUTOR, 'student_uid': STUDENT, 'status': self.link_status}]
            return []
        if sql.startswith('SELECT tutor_user_id, student_user_id FROM chat_messages'):
            a, b = params['a'], params['b']
            return [{'tutor_user_id': r['tutor_user_id'], 'student_user_id': r['student_user_id']}
                    for r in self.rows.values() if {r['tutor_user_id'], r['student_user_id']} == {a, b}][:1]
        if sql.startswith('SELECT * FROM chat_messages WHERE tutor_user_id'):
            rows = sorted(self.rows.values(), key=lambda r: -r['id'])
            return rows[:params['lim']]
        if sql.startswith('SELECT count(*) AS n FROM chat_messages WHERE tutor_user_id'):
            return [{'n': len(self.rows)}]
        if sql.startswith('DELETE FROM chat_messages'):
            ids = sorted(self.rows)[:params['n']]
            for i in ids:
                del self.rows[i]
            return [{'id': i} for i in ids]
        if sql.startswith('UPDATE chat_messages SET read_at'):
            hit = [r for r in self.rows.values() if r['sender_id'] == params['p'] and r['read_at'] is None]
            for r in hit:
                r['read_at'] = params['t']
            return [{'id': r['id']} for r in hit]
        return []

    async def create(self, table, data):
        self.seq += 1
        self.rows[self.seq] = {**data, 'id': self.seq, 'read_at': None}
        return self.rows[self.seq]

    async def read(self, table, rid):
        return self.rows.get(rid)


def run(coro):
    return asyncio.run(coro)


def send(db, me, partner, text='привет'):
    return run(chat.Send(db=db).execute(chat.SendDTO(me_id=me, partner_id=partner, text=text)))


def test_linked_users_write_to_each_other():
    db = Stub()
    res = send(db, STUDENT, TUTOR)
    assert res.recipient_id == TUTOR and res.message.tutor_user_id == TUTOR and res.message.student_user_id == STUDENT
    assert send(db, TUTOR, STUDENT, 'ответ').message.sender_id == TUTOR


def test_without_link_history_is_read_only_and_strangers_have_no_dialog():
    db = Stub()
    send(db, STUDENT, TUTOR)
    db.link_status = None  # связь удалили
    with pytest.raises(ForbiddenError):
        send(db, STUDENT, TUTOR)
    history = run(chat.History(db=db).execute(chat.HistoryDTO(me_id=STUDENT, partner_id=TUTOR)))
    assert len(history.items) == 1
    with pytest.raises(NotFoundError):
        send(db, STRANGER, TUTOR)
    pending = Stub(link_status='PENDING')
    with pytest.raises(ForbiddenError):
        send(pending, STUDENT, TUTOR)


def test_overflow_removes_oldest_200():
    db = Stub()
    for i in range(chat.KEEP_LIMIT):
        db.rows[i + 1] = {'id': i + 1, 'tutor_user_id': TUTOR, 'student_user_id': STUDENT, 'sender_id': TUTOR,
                          'text': 'x', 'created_at': datetime.datetime.now(datetime.timezone.utc), 'read_at': None}
    db.seq = chat.KEEP_LIMIT
    res = send(db, STUDENT, TUTOR, 'новое')
    assert res.trimmed == chat.TRIM_COUNT
    assert len(db.rows) == chat.KEEP_LIMIT + 1 - chat.TRIM_COUNT
    assert min(db.rows) == chat.TRIM_COUNT + 1 and res.message.id in db.rows


def test_read_marks_partner_messages_only():
    db = Stub()
    send(db, TUTOR, STUDENT)
    send(db, STUDENT, TUTOR)
    res = run(chat.MarkRead(db=db).execute(chat.DialogDTO(me_id=STUDENT, partner_id=TUTOR)))
    assert res.count == 1
    assert [r['read_at'] is not None for r in db.rows.values()] == [True, False]
