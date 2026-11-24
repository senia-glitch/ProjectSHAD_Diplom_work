"""Доступ учеников к тесту и список учеников репетитора.

Выдать доступ можно только ученику, связанному с репетитором (configurations).
Уже выданный доступ после разрыва связи остаётся видимым и снимается репетитором.
"""
from core import BaseScenario, NotFoundError, register_scenario
from pydantic import BaseModel, Field

from app.scenarios.testing.common import now
from app.scenarios.testing.quizzes import ActorDTO, load_owned

LINKED_STUDENTS = (
    'SELECT u.id AS student_id, u.username, u.full_name FROM configurations c '
    'JOIN tutors t ON t.id = c.tutor_id JOIN students s ON s.id = c.student_id '
    'JOIN users u ON u.id = s.user_id WHERE t.user_id = :owner')


class AccessListDTO(BaseModel):
    actor_id: int = Field(gt=0)
    test_id: int = Field(gt=0)


class SetAccessDTO(AccessListDTO):
    student_id: int = Field(gt=0)
    enabled: bool


class AccessItem(BaseModel):
    student_id: int
    username: str
    full_name: str
    enabled: bool
    attempts: int
    linked: bool = True


class AccessList(BaseModel):
    items: list[AccessItem]


class StudentItem(BaseModel):
    id: int
    username: str
    full_name: str


class StudentList(BaseModel):
    items: list[StudentItem]


@register_scenario('testing.list_students', dto=ActorDTO, response=StudentList)
class ListMyStudents(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(LINKED_STUDENTS + ' ORDER BY u.full_name, u.id', {'owner': dto.actor_id})
        return StudentList(items=[StudentItem(id=r['student_id'], username=r['username'], full_name=r['full_name'])
                                  for r in rows])


@register_scenario('testing.access_list', dto=AccessListDTO, response=AccessList)
class ListAccess(BaseScenario):
    async def execute(self, dto):
        row = await load_owned(self._db, dto.actor_id, dto.test_id)
        rows = await self._db.query(
            'WITH linked AS (' + LINKED_STUDENTS + '), '
            'granted AS (SELECT u.id AS student_id, u.username, u.full_name FROM quiz_access a '
            '            JOIN users u ON u.id = a.student_id WHERE a.quiz_id = :t), '
            'everyone AS (SELECT * FROM linked UNION SELECT * FROM granted) '
            'SELECT e.student_id, e.username, e.full_name, '
            ' EXISTS (SELECT 1 FROM quiz_access a WHERE a.quiz_id = :t AND a.student_id = e.student_id) AS enabled, '
            ' EXISTS (SELECT 1 FROM linked l WHERE l.student_id = e.student_id) AS linked, '
            ' (SELECT count(*) FROM quiz_attempts p WHERE p.quiz_id = :t AND p.student_id = e.student_id '
            '  AND p.quiz_version = :v) AS attempts '
            'FROM everyone e ORDER BY e.full_name, e.student_id',
            {'owner': dto.actor_id, 't': dto.test_id, 'v': row['version']})
        return AccessList(items=[AccessItem(**r) for r in rows])


@register_scenario('testing.access_set', dto=SetAccessDTO, response=AccessItem)
class SetAccess(BaseScenario):
    async def execute(self, dto):
        await load_owned(self._db, dto.actor_id, dto.test_id)
        linked = await self._db.query(LINKED_STUDENTS + ' AND u.id = :s', {'owner': dto.actor_id, 's': dto.student_id})
        params = {'t': dto.test_id, 's': dto.student_id}
        if dto.enabled:
            if not linked:
                raise NotFoundError('Ученик не найден среди ваших учеников')
            await self._db.query(
                'INSERT INTO quiz_access (quiz_id, student_id, granted_at) VALUES (:t, :s, :at) '
                'ON CONFLICT (quiz_id, student_id) DO NOTHING', params | {'at': now()}, channel='write')
        else:
            await self._db.query('DELETE FROM quiz_access WHERE quiz_id = :t AND student_id = :s',
                                 params, channel='write')
        student = await self._db.read('users', dto.student_id)
        if student is None:
            raise NotFoundError('Ученик не найден')
        count = await self._db.query(
            'SELECT count(*) AS n FROM quiz_attempts p JOIN quizzes t ON t.id = p.quiz_id '
            'WHERE p.quiz_id = :t AND p.student_id = :s AND p.quiz_version = t.version', params)
        return AccessItem(student_id=student['id'], username=student['username'], full_name=student['full_name'],
                          enabled=dto.enabled, attempts=count[0]['n'], linked=bool(linked))
