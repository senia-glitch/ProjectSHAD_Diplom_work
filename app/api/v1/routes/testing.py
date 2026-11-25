"""Внешние сценарии модуля тестирования: тесты репетитора и прохождение учеником."""
from typing import Any, Literal

from core import run
from fastapi import APIRouter, Depends, Path, Response
from pydantic import BaseModel, Field

from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.testing.access import AccessItem, AccessList, AccessListDTO, SetAccessDTO, StudentList
from app.scenarios.testing.attempts import (ActorDTO as AttemptActorDTO, AttemptDetail, AttemptList, AttemptRefDTO,
                                            AttemptSummary, ReviewDTO, StudentResultsDTO, SubmitDTO,
                                            TestRefDTO)
from app.scenarios.testing.quizzes import (ActorDTO, CreateQuizDTO, OwnedQuizDTO, QuizDetail, QuizInput, QuizList,
                                           UpdateQuizDTO)

router = APIRouter(prefix='/testing', tags=['testing'])


class AccessBody(BaseModel):
    enabled: bool


class ReviewBody(BaseModel):
    teacher_grade: Literal['удовлетворительно', 'хорошо', 'замечательно'] | None = None
    teacher_comment: str = Field(default='', max_length=5000)


class SubmitBody(BaseModel):
    version: int = Field(gt=0)
    answers: dict[str, Any]


# ---------- репетитор ----------

@router.get('/tutor/tests', response_model=QuizList)
@external_scenario('testing.list_own', core='testing.list_owned')
async def list_tests(user: dict = Depends(get_current_user)):
    return await run('testing.list_owned', ActorDTO(actor_id=user['user_id']))


@router.post('/tutor/tests', status_code=201, response_model=QuizDetail)
@external_scenario('testing.create', core='testing.create')
async def create_test(body: QuizInput, user: dict = Depends(get_current_user)):
    return await run('testing.create', CreateQuizDTO(**body.model_dump(), actor_id=user['user_id']))


@router.get('/tutor/tests/{test_id}', response_model=QuizDetail)
@external_scenario('testing.get_own', core='testing.get_owned')
async def get_test(test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.get_owned', OwnedQuizDTO(actor_id=user['user_id'], test_id=test_id))


@router.put('/tutor/tests/{test_id}', response_model=QuizDetail)
@external_scenario('testing.update', core='testing.update')
async def update_test(body: QuizInput, test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.update', UpdateQuizDTO(**body.model_dump(), actor_id=user['user_id'], test_id=test_id))


@router.delete('/tutor/tests/{test_id}', status_code=204)
@external_scenario('testing.delete', core='testing.delete')
async def delete_test(test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    await run('testing.delete', OwnedQuizDTO(actor_id=user['user_id'], test_id=test_id))
    return Response(status_code=204)


@router.get('/tutor/students', response_model=StudentList)
@external_scenario('testing.list_students', core='testing.list_students')
async def list_students(user: dict = Depends(get_current_user)):
    return await run('testing.list_students', ActorDTO(actor_id=user['user_id']))


@router.get('/tutor/tests/{test_id}/access', response_model=AccessList)
@external_scenario('testing.access_list', core='testing.access_list')
async def list_access(test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.access_list', AccessListDTO(actor_id=user['user_id'], test_id=test_id))


@router.put('/tutor/tests/{test_id}/access/{student_id}', response_model=AccessItem)
@external_scenario('testing.access_set', core='testing.access_set')
async def set_access(body: AccessBody, test_id: int = Path(gt=0), student_id: int = Path(gt=0),
                     user: dict = Depends(get_current_user)):
    return await run('testing.access_set', SetAccessDTO(actor_id=user['user_id'], test_id=test_id,
                                                        student_id=student_id, enabled=body.enabled))


@router.get('/tutor/tests/{test_id}/results', response_model=AttemptList)
@external_scenario('testing.results_for_test', core='testing.attempts_list_for_test')
async def list_results(test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.attempts_list_for_test', TestRefDTO(actor_id=user['user_id'], test_id=test_id))


@router.get('/tutor/students/{student_id}/results', response_model=AttemptList)
@external_scenario('testing.results_for_student', core='testing.attempts_list_for_student')
async def student_results(student_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.attempts_list_for_student', StudentResultsDTO(actor_id=user['user_id'], student_id=student_id))


@router.get('/tutor/results/{attempt_id}', response_model=AttemptDetail)
@external_scenario('testing.result_for_tutor', core='testing.attempts_get_for_teacher')
async def get_result(attempt_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.attempts_get_for_teacher', AttemptRefDTO(actor_id=user['user_id'], attempt_id=attempt_id))


@router.put('/tutor/results/{attempt_id}/review', response_model=AttemptSummary)
@external_scenario('testing.review', core='testing.attempts_review')
async def review(body: ReviewBody, attempt_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.attempts_review',
                     ReviewDTO(actor_id=user['user_id'], attempt_id=attempt_id, **body.model_dump()))


# ---------- ученик ----------

@router.get('/student/tests', response_model=QuizList)
@external_scenario('testing.list_available', core='testing.list_available')
async def available(user: dict = Depends(get_current_user)):
    return await run('testing.list_available', ActorDTO(actor_id=user['user_id']))


@router.get('/student/tests/{test_id}', response_model=QuizDetail)
@external_scenario('testing.open', core='testing.get_for_student')
async def open_test(test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.get_for_student', OwnedQuizDTO(actor_id=user['user_id'], test_id=test_id))


@router.post('/student/tests/{test_id}/attempts', status_code=201, response_model=AttemptDetail)
@external_scenario('testing.submit', core='testing.attempts_submit')
async def submit(body: SubmitBody, test_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.attempts_submit',
                     SubmitDTO(actor_id=user['user_id'], test_id=test_id, **body.model_dump()))


@router.get('/student/results', response_model=AttemptList)
@external_scenario('testing.results_mine', core='testing.attempts_list_mine')
async def my_results(user: dict = Depends(get_current_user)):
    return await run('testing.attempts_list_mine', AttemptActorDTO(actor_id=user['user_id']))


@router.get('/student/results/{attempt_id}', response_model=AttemptDetail)
@external_scenario('testing.result_mine', core='testing.attempts_get_mine')
async def my_result(attempt_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('testing.attempts_get_mine', AttemptRefDTO(actor_id=user['user_id'], attempt_id=attempt_id))
