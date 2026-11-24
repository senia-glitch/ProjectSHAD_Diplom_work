"""Тесты репетитора: создание, изменение (новая версия), удаление, выдача ученику.

Идентификаторы участников — users.id. Владелец теста — репетитор (роль проверяет политика доступа).
"""
from datetime import datetime
from typing import Any

from core import BaseScenario, NotFoundError, register_scenario
from pydantic import BaseModel, Field, model_validator

from app.scenarios.testing.common import BadRequestError, dumps, loads, now
from app.scenarios.testing.tasks import TaskError, for_student, validate_tasks


class QuizInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=20000)  # Markdown
    tasks: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    good_percent: int = Field(default=60, ge=1, le=100)
    excellent_percent: int = Field(default=85, ge=1, le=100)

    @model_validator(mode='after')
    def thresholds(self):
        if self.good_percent >= self.excellent_percent:
            raise ValueError('Порог «хорошо» должен быть меньше порога «замечательно»')
        self.title = ' '.join(self.title.split())
        if not self.title:
            raise ValueError('Укажите название теста')
        return self


class CreateQuizDTO(QuizInput):
    actor_id: int = Field(gt=0)


class UpdateQuizDTO(QuizInput):
    actor_id: int = Field(gt=0)
    test_id: int = Field(gt=0)


class OwnedQuizDTO(BaseModel):
    actor_id: int = Field(gt=0)
    test_id: int = Field(gt=0)


class ActorDTO(BaseModel):
    actor_id: int = Field(gt=0)


class QuizSummary(BaseModel):
    id: int
    title: str
    description: str
    version: int
    task_count: int
    max_points: float
    updated_at: datetime
    owner_name: str = ''
    access_count: int = 0
    attempt_count: int = 0
    my_attempts: int = 0
    my_last_grade: str | None = None


class QuizDetail(BaseModel):
    id: int
    title: str
    description: str
    version: int
    good_percent: int
    excellent_percent: int
    tasks: list[dict[str, Any]]
    updated_at: datetime


class QuizList(BaseModel):
    items: list[QuizSummary]


def _validated(dto):
    try:
        return validate_tasks(dto.tasks)
    except TaskError as error:
        raise BadRequestError(str(error)) from None


def _detail(row, tasks):
    return QuizDetail(id=row['id'], title=row['title'], description=row['description'], version=row['version'],
                      good_percent=row['good_percent'], excellent_percent=row['excellent_percent'],
                      tasks=tasks, updated_at=row['updated_at'])


def _summary(row, **extra):
    tasks = loads(row['tasks'], [])
    return QuizSummary(id=row['id'], title=row['title'], description=row['description'], version=row['version'],
                       task_count=len(tasks), updated_at=row['updated_at'],
                       max_points=sum(t['points'] for t in tasks if t.get('answer') is not None), **extra)


async def load_owned(db, actor_id, test_id):
    """Тест репетитора; чужой и отсутствующий тест неразличимы."""
    row = await db.read('quizzes', test_id)
    if row is None or row['owner_id'] != actor_id:
        raise NotFoundError('Тест не найден')
    return row


async def has_access(db, student_id, test_id):
    rows = await db.query('SELECT 1 AS ok FROM quiz_access WHERE quiz_id = :t AND student_id = :s',
                          {'t': test_id, 's': student_id})
    return bool(rows)


def student_tasks(row, student_id):
    seed = f'{student_id}:{row["id"]}:{row["version"]}'
    return [for_student(t, seed) for t in loads(row['tasks'], [])]


@register_scenario('testing.create', dto=CreateQuizDTO, response=QuizDetail)
class CreateQuiz(BaseScenario):
    async def execute(self, dto):
        tasks, stamp = _validated(dto), now()
        row = await self._db.create('quizzes', {
            'owner_id': dto.actor_id, 'title': dto.title, 'description': dto.description.strip(),
            'tasks': dumps(tasks), 'version': 1, 'good_percent': dto.good_percent,
            'excellent_percent': dto.excellent_percent, 'created_at': stamp, 'updated_at': stamp})
        return _detail(row, tasks)


@register_scenario('testing.update', dto=UpdateQuizDTO, response=QuizDetail)
class UpdateQuiz(BaseScenario):
    async def execute(self, dto):
        tasks = _validated(dto)
        await load_owned(self._db, dto.actor_id, dto.test_id)
        # Атомарное увеличение версии: прежние результаты становятся устаревшими для учеников.
        rows = await self._db.query(
            'UPDATE quizzes SET title = :title, description = :description, tasks = :tasks, version = version + 1, '
            'good_percent = :good, excellent_percent = :excellent, updated_at = :stamp '
            'WHERE id = :id AND owner_id = :owner RETURNING *',
            {'title': dto.title, 'description': dto.description.strip(), 'tasks': dumps(tasks),
             'good': dto.good_percent, 'excellent': dto.excellent_percent, 'stamp': now(),
             'id': dto.test_id, 'owner': dto.actor_id}, channel='write')
        if not rows:
            raise NotFoundError('Тест не найден')
        return _detail(rows[0], tasks)


@register_scenario('testing.delete', dto=OwnedQuizDTO)
class DeleteQuiz(BaseScenario):
    async def execute(self, dto):
        await load_owned(self._db, dto.actor_id, dto.test_id)
        if not await self._db.delete('quizzes', dto.test_id):  # доступы и результаты удаляются каскадно
            raise NotFoundError('Тест не найден')


@register_scenario('testing.get_owned', dto=OwnedQuizDTO, response=QuizDetail)
class GetOwnedQuiz(BaseScenario):
    async def execute(self, dto):
        row = await load_owned(self._db, dto.actor_id, dto.test_id)
        return _detail(row, loads(row['tasks'], []))


@register_scenario('testing.list_owned', dto=ActorDTO, response=QuizList)
class ListOwnedQuizzes(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(
            'SELECT t.*, (SELECT count(*) FROM quiz_access a WHERE a.quiz_id = t.id) AS access_count, '
            '(SELECT count(*) FROM quiz_attempts p WHERE p.quiz_id = t.id) AS attempt_count '
            'FROM quizzes t WHERE t.owner_id = :owner ORDER BY t.updated_at DESC, t.id DESC', {'owner': dto.actor_id})
        return QuizList(items=[_summary(r, access_count=r['access_count'], attempt_count=r['attempt_count'])
                               for r in rows])


@register_scenario('testing.list_available', dto=ActorDTO, response=QuizList)
class ListAvailableQuizzes(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(
            'SELECT t.*, o.full_name AS owner_name, '
            '(SELECT count(*) FROM quiz_attempts p WHERE p.quiz_id = t.id AND p.student_id = :s '
            ' AND p.quiz_version = t.version) AS my_attempts, '
            '(SELECT coalesce(p.teacher_grade, p.auto_grade) FROM quiz_attempts p WHERE p.quiz_id = t.id '
            ' AND p.student_id = :s AND p.quiz_version = t.version ORDER BY p.submitted_at DESC LIMIT 1) AS my_last_grade '
            'FROM quizzes t JOIN quiz_access a ON a.quiz_id = t.id AND a.student_id = :s '
            'JOIN users o ON o.id = t.owner_id '
            'ORDER BY t.updated_at DESC, t.id DESC', {'s': dto.actor_id})
        return QuizList(items=[_summary(r, owner_name=r['owner_name'], my_attempts=r['my_attempts'],
                                        my_last_grade=r['my_last_grade']) for r in rows])


@register_scenario('testing.get_for_student', dto=OwnedQuizDTO, response=QuizDetail)
class GetQuizForStudent(BaseScenario):
    async def execute(self, dto):
        row = await self._db.read('quizzes', dto.test_id)
        if row is None or not await has_access(self._db, dto.actor_id, dto.test_id):
            raise NotFoundError('Тест недоступен')
        return _detail(row, student_tasks(row, dto.actor_id))
