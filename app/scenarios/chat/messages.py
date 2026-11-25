"""Личный чат «репетитор — ученик».

Один диалог на пару пользователей, связанных связью (configurations). Пока связь
действует — можно писать; после её удаления история остаётся только для чтения.
В диалоге хранится не больше KEEP_LIMIT сообщений: при достижении удаляются
TRIM_COUNT самых старых.
"""
from datetime import datetime, timezone

from core import BaseScenario, NotFoundError, ValidationError, register_scenario
from pydantic import BaseModel, Field, field_validator

from app.core.exceptions import ForbiddenError

KEEP_LIMIT = 1000
TRIM_COUNT = 200
TEXT_MAX = 2000
PAGE = 50


def _now():
    return datetime.now(timezone.utc)


# ---------- DTO ----------

class MeDTO(BaseModel):
    me_id: int = Field(gt=0)


class DialogDTO(MeDTO):
    partner_id: int = Field(gt=0)


class HistoryDTO(DialogDTO):
    before_id: int | None = Field(default=None, gt=0)
    limit: int = Field(default=PAGE, ge=1, le=100)


class SendDTO(DialogDTO):
    text: str = Field(min_length=1, max_length=TEXT_MAX)

    @field_validator('text')
    @classmethod
    def _text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Напишите сообщение')
        return value


class Message(BaseModel):
    id: int
    sender_id: int
    partner_id: int  # собеседник получателя этого объекта не важен: клиент сопоставляет по паре
    tutor_user_id: int
    student_user_id: int
    text: str
    created_at: datetime
    read_at: datetime | None = None


class Dialog(BaseModel):
    partner_id: int
    partner_name: str
    partner_avatar: str | None = None
    partner_role: str
    can_write: bool
    unread: int = 0
    last_text: str | None = None
    last_at: datetime | None = None
    last_from_me: bool = False


class DialogList(BaseModel):
    items: list[Dialog]
    unread_total: int = 0


class MessageList(BaseModel):
    items: list[Message]
    has_more: bool = False


class SendResult(BaseModel):
    message: Message
    recipient_id: int
    trimmed: int = 0


class ReadResult(BaseModel):
    partner_id: int
    count: int


class UnreadCount(BaseModel):
    count: int


# ---------- пара и права ----------

async def _links(db, me_id: int) -> dict[int, dict]:
    """Связи пользователя: собеседник → {tutor, student, active}."""
    rows = await db.query(
        'SELECT t.user_id AS tutor_uid, s.user_id AS student_uid, c.status FROM configurations c '
        'JOIN tutors t ON t.id = c.tutor_id JOIN students s ON s.id = c.student_id '
        'WHERE t.user_id = :me OR s.user_id = :me', {'me': me_id})
    result = {}
    for r in rows:
        partner = r['student_uid'] if r['tutor_uid'] == me_id else r['tutor_uid']
        result[partner] = {'tutor': r['tutor_uid'], 'student': r['student_uid'],
                           'active': (r['status'] or 'ACTIVE') == 'ACTIVE'}
    return result


async def _pair(db, me_id: int, partner_id: int) -> dict:
    """Пара диалога. Без связи и без истории — диалога нет."""
    links = await _links(db, me_id)
    if partner_id in links:
        return links[partner_id]
    rows = await db.query(
        'SELECT tutor_user_id, student_user_id FROM chat_messages '
        'WHERE (tutor_user_id = :a AND student_user_id = :b) OR (tutor_user_id = :b AND student_user_id = :a) LIMIT 1',
        {'a': me_id, 'b': partner_id})
    if not rows:
        raise NotFoundError('Диалог не найден')
    return {'tutor': rows[0]['tutor_user_id'], 'student': rows[0]['student_user_id'], 'active': False}


def _message(row, me_id: int | None = None) -> Message:
    partner = row['student_user_id'] if row['sender_id'] == row['tutor_user_id'] else row['tutor_user_id']
    return Message(id=row['id'], sender_id=row['sender_id'], partner_id=partner,
                   tutor_user_id=row['tutor_user_id'], student_user_id=row['student_user_id'],
                   text=row['text'], created_at=row['created_at'], read_at=row.get('read_at'))


# ---------- сценарии ----------

@register_scenario('chat.dialogs', dto=MeDTO, response=DialogList)
class Dialogs(BaseScenario):
    """Диалоги пользователя: все связи и прежние собеседники с историей."""
    async def execute(self, dto):
        links = await _links(self._db, dto.me_id)
        history = await self._db.query(
            'SELECT DISTINCT ON (tutor_user_id, student_user_id) tutor_user_id, student_user_id, sender_id, text, '
            'created_at FROM chat_messages WHERE tutor_user_id = :me OR student_user_id = :me '
            'ORDER BY tutor_user_id, student_user_id, id DESC', {'me': dto.me_id})
        last = {}
        for r in history:
            partner = r['student_user_id'] if r['tutor_user_id'] == dto.me_id else r['tutor_user_id']
            last[partner] = r
        unread_rows = await self._db.query(
            'SELECT sender_id, count(*) AS n FROM chat_messages WHERE (tutor_user_id = :me OR student_user_id = :me) '
            'AND sender_id <> :me AND read_at IS NULL GROUP BY sender_id', {'me': dto.me_id})
        unread = {r['sender_id']: int(r['n']) for r in unread_rows}
        partners = set(links) | set(last)
        if not partners:
            return DialogList(items=[])
        users = await self._db.query(
            'SELECT u.id, u.full_name, u.avatar_url, r.name AS role FROM users u JOIN roles r ON r.id = u.role_id '
            'WHERE u.id = ANY(:ids)', {'ids': list(partners)})
        items = []
        for u in users:
            m = last.get(u['id'])
            items.append(Dialog(
                partner_id=u['id'], partner_name=u['full_name'], partner_avatar=u.get('avatar_url'),
                partner_role=u['role'], can_write=bool(links.get(u['id'], {}).get('active')),
                unread=unread.get(u['id'], 0), last_text=(m['text'][:140] if m else None),
                last_at=(m['created_at'] if m else None), last_from_me=bool(m and m['sender_id'] == dto.me_id)))
        far_past = datetime.min.replace(tzinfo=timezone.utc)
        items.sort(key=lambda d: (d.last_at or far_past, d.partner_name), reverse=True)
        return DialogList(items=items, unread_total=sum(unread.values()))


@register_scenario('chat.messages', dto=HistoryDTO, response=MessageList)
class History(BaseScenario):
    """История диалога порциями: последние сообщения, «раньше» — по before_id."""
    async def execute(self, dto):
        pair = await _pair(self._db, dto.me_id, dto.partner_id)
        params = {'t': pair['tutor'], 's': pair['student'], 'lim': dto.limit + 1}
        older = ''
        if dto.before_id:
            older = 'AND id < :before '
            params['before'] = dto.before_id
        rows = await self._db.query(
            'SELECT * FROM chat_messages WHERE tutor_user_id = :t AND student_user_id = :s '
            f'{older}ORDER BY id DESC LIMIT :lim', params)
        has_more = len(rows) > dto.limit
        rows = list(reversed(rows[:dto.limit]))
        return MessageList(items=[_message(r) for r in rows], has_more=has_more)


@register_scenario('chat.send', dto=SendDTO, response=SendResult)
class Send(BaseScenario):
    """Сообщение собеседнику по действующей связи; при переполнении удаляются старые."""
    async def execute(self, dto):
        if dto.partner_id == dto.me_id:
            raise ValidationError('Нельзя написать самому себе')
        pair = await _pair(self._db, dto.me_id, dto.partner_id)
        if not pair['active']:
            raise ForbiddenError('Связи с этим пользователем нет — писать нельзя, история доступна для чтения')
        row = await self._db.create('chat_messages', {
            'tutor_user_id': pair['tutor'], 'student_user_id': pair['student'], 'sender_id': dto.me_id,
            'text': dto.text, 'created_at': _now()})
        trimmed = 0
        count = await self._db.query(
            'SELECT count(*) AS n FROM chat_messages WHERE tutor_user_id = :t AND student_user_id = :s',
            {'t': pair['tutor'], 's': pair['student']})
        if int(count[0]['n']) > KEEP_LIMIT:
            removed = await self._db.query(
                'DELETE FROM chat_messages WHERE id IN (SELECT id FROM chat_messages '
                'WHERE tutor_user_id = :t AND student_user_id = :s ORDER BY id LIMIT :n) RETURNING id',
                {'t': pair['tutor'], 's': pair['student'], 'n': TRIM_COUNT}, channel='write')
            trimmed = len(removed or [])
        saved = await self._db.read('chat_messages', row['id'])
        return SendResult(message=_message(saved), recipient_id=dto.partner_id, trimmed=trimmed)


@register_scenario('chat.read', dto=DialogDTO, response=ReadResult)
class MarkRead(BaseScenario):
    """Отметить прочитанными все сообщения собеседника в диалоге."""
    async def execute(self, dto):
        pair = await _pair(self._db, dto.me_id, dto.partner_id)
        rows = await self._db.query(
            'UPDATE chat_messages SET read_at = :t WHERE tutor_user_id = :tu AND student_user_id = :su '
            'AND sender_id = :p AND read_at IS NULL RETURNING id',
            {'t': _now(), 'tu': pair['tutor'], 'su': pair['student'], 'p': dto.partner_id}, channel='write')
        return ReadResult(partner_id=dto.partner_id, count=len(rows or []))


@register_scenario('chat.unread', dto=MeDTO, response=UnreadCount)
class Unread(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(
            'SELECT count(*) AS n FROM chat_messages WHERE (tutor_user_id = :me OR student_user_id = :me) '
            'AND sender_id <> :me AND read_at IS NULL', {'me': dto.me_id})
        return UnreadCount(count=int(rows[0]['n']) if rows else 0)
