"""Прохождение теста и результаты: автопроверка, видимость, оценка репетитора."""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
from core import BaseScenario, ConflictError, NotFoundError, register_scenario
from app.scenarios.testing.common import BadRequestError, dumps, loads, now, sanitize_html
from app.scenarios.testing.quizzes import has_access, load_owned, student_tasks
from app.scenarios.testing.tasks import auto_grade, grade_attempt

Grade = Literal['удовлетворительно', 'хорошо', 'замечательно']
MAX_ANSWERS_SIZE = 300_000


class SubmitDTO(BaseModel):
    actor_id: int = Field(gt=0)
    test_id: int = Field(gt=0)
    version: int = Field(gt=0)
    answers: dict[str, Any]


class ActorDTO(BaseModel):
    actor_id: int = Field(gt=0)


class AttemptRefDTO(BaseModel):
    actor_id: int = Field(gt=0)
    attempt_id: int = Field(gt=0)


class TestRefDTO(BaseModel):
    actor_id: int = Field(gt=0)
    test_id: int = Field(gt=0)


class ReviewDTO(AttemptRefDTO):
    teacher_grade: Grade | None = None
    teacher_comment: str = Field(default='', max_length=5000)


class AttemptSummary(BaseModel):
    id: int
    test_id: int
    test_title: str
    student_id: int
    student_name: str
    score: float
    max_score: float
    auto_grade: str | None
    teacher_grade: str | None
    teacher_comment: str
    submitted_at: datetime
    reviewed_at: datetime | None
    outdated: bool = False


class AttemptDetail(AttemptSummary):
    tasks: list[dict[str, Any]]
    answers: dict[str, Any]
    results: dict[str, Any]


class AttemptList(BaseModel):
    items: list[AttemptSummary]


SELECT = (
    'SELECT p.*, t.title AS test_title, t.version AS current_version, t.owner_id, u.full_name AS student_name '
    'FROM quiz_attempts p JOIN quizzes t ON t.id = p.quiz_id JOIN users u ON u.id = p.student_id ')


def _summary(row):
    return AttemptSummary(
        id=row['id'], test_id=row['quiz_id'], test_title=row['test_title'], student_id=row['student_id'],
        student_name=row['student_name'], score=row['score'], max_score=row['max_score'],
        auto_grade=row['auto_grade'], teacher_grade=row['teacher_grade'], teacher_comment=row['teacher_comment'],
        submitted_at=row['submitted_at'], reviewed_at=row['reviewed_at'],
        outdated=row['quiz_version'] != row['current_version'])


def _clean_answers(tasks, answers):
    """Оставляет ответы только на задания теста; форматированный текст очищается."""
    if len(dumps(answers)) > MAX_ANSWERS_SIZE:
        raise BadRequestError('Слишком большой объём ответов')
    clean = {}
    for task in tasks:
        given = answers.get(task['id'])
        if not isinstance(given, dict):
            continue
        if task['kind'] == 'open' and task['variant'] == 'rich':
            given = {'html': sanitize_html(given.get('html'))}
        clean[task['id']] = given
    return clean


@register_scenario('testing.attempts_submit', dto=SubmitDTO, response=AttemptDetail)
class SubmitAttempt(BaseScenario):
    async def execute(self, dto):
        test = await self._db.read('quizzes', dto.test_id)
        if test is None or not await has_access(self._db, dto.actor_id, dto.test_id):
            raise NotFoundError('Тест недоступен')
        if test['version'] != dto.version:
            raise ConflictError('Тест был изменён преподавателем. Откройте его заново')
        tasks = loads(test['tasks'], [])
        answers = _clean_answers(tasks, dto.answers)
        results, score, max_score = grade_attempt(tasks, answers)
        row = await self._db.create('quiz_attempts', {
            'quiz_id': test['id'], 'student_id': dto.actor_id, 'quiz_version': test['version'],
            'answers': dumps(answers), 'results': dumps(results), 'score': score, 'max_score': max_score,
            'auto_grade': auto_grade(score, max_score, test['good_percent'], test['excellent_percent']),
            'teacher_grade': None, 'teacher_comment': '', 'submitted_at': now(), 'reviewed_at': None})
        return await run_detail(self._db, row['id'], student_id=dto.actor_id)


async def _load(db, attempt_id):
    rows = await db.query(SELECT + 'WHERE p.id = :id', {'id': attempt_id})
    if not rows:
        raise NotFoundError('Результат не найден')
    return rows[0]


async def run_detail(db, attempt_id, *, student_id=None, teacher_id=None):
    row = await _load(db, attempt_id)
    summary = _summary(row)
    if student_id is not None:
        # Ученик видит только свои результаты по существующему и не изменённому тесту.
        if row['student_id'] != student_id or summary.outdated:
            raise NotFoundError('Результат не найден')
        test = await db.read('quizzes', row['quiz_id'])
        tasks = student_tasks(test, student_id)
    else:
        if row['owner_id'] != teacher_id:
            raise NotFoundError('Результат не найден')
        test = await db.read('quizzes', row['quiz_id'])
        tasks = [] if summary.outdated else loads(test['tasks'], [])
    return AttemptDetail(**summary.model_dump(), tasks=tasks,
                         answers=loads(row['answers'], {}), results=loads(row['results'], {}))


@register_scenario('testing.attempts_list_mine', dto=ActorDTO, response=AttemptList)
class ListMyAttempts(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(
            SELECT + 'WHERE p.student_id = :s AND p.quiz_version = t.version ORDER BY p.submitted_at DESC',
            {'s': dto.actor_id})
        return AttemptList(items=[_summary(r) for r in rows])


@register_scenario('testing.attempts_get_mine', dto=AttemptRefDTO, response=AttemptDetail)
class GetMyAttempt(BaseScenario):
    async def execute(self, dto):
        return await run_detail(self._db, dto.attempt_id, student_id=dto.actor_id)


@register_scenario('testing.attempts_list_for_test', dto=TestRefDTO, response=AttemptList)
class ListTestAttempts(BaseScenario):
    async def execute(self, dto):
        await load_owned(self._db, dto.actor_id, dto.test_id)
        rows = await self._db.query(SELECT + 'WHERE p.quiz_id = :t ORDER BY p.submitted_at DESC', {'t': dto.test_id})
        return AttemptList(items=[_summary(r) for r in rows])


@register_scenario('testing.attempts_get_for_teacher', dto=AttemptRefDTO, response=AttemptDetail)
class GetAttemptForTeacher(BaseScenario):
    async def execute(self, dto):
        return await run_detail(self._db, dto.attempt_id, teacher_id=dto.actor_id)


@register_scenario('testing.attempts_review', dto=ReviewDTO, response=AttemptSummary)
class ReviewAttempt(BaseScenario):
    async def execute(self, dto):
        row = await _load(self._db, dto.attempt_id)
        if row['owner_id'] != dto.actor_id:
            raise NotFoundError('Результат не найден')
        await self._db.update('quiz_attempts', dto.attempt_id, {
            'teacher_grade': dto.teacher_grade, 'teacher_comment': dto.teacher_comment.strip(), 'reviewed_at': now()})
        return _summary(await _load(self._db, dto.attempt_id))
