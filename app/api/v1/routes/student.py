from fastapi import APIRouter, Depends, Header, Query
from core import run
from app.api.v1.dependencies import get_current_user, require_auth

from app.scenarios.student.profile import StudentGetMyProfileDTO, StudentUpdateMySettingsDTO
from app.scenarios.student.lessons import (
    StudentGetMyLessonsDTO, StudentGetLessonDTO, StudentGetTutorLessonsDTO,
    StudentCreateLessonDTO, StudentJoinLessonDTO, StudentLeaveLessonDTO,
)
from app.scenarios.student.configurations import (
    StudentGetMyConfigurationsDTO, StudentGetConfigurationDTO,
    StudentCreateConfigurationDTO, StudentCreateConfigurationByCodeDTO,
    StudentDeleteConfigurationDTO,
)
from app.scenarios.student.tutors import StudentGetAvailableSlotsDTO

router = APIRouter(prefix="/student", tags=["student"])


# === Profile ===

@router.get("/me")
@require_auth(["student"])
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("student_get_my_profile", dto)


@router.patch("/me/settings")
@require_auth(["student"])
async def update_my_settings(
    dto: StudentUpdateMySettingsDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_update_my_settings", dto)


# === Lessons ===

@router.get("/me/lessons")
@require_auth(["student"])
async def get_my_lessons(
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetMyLessonsDTO(
        access_token=authorization.split(" ")[1],
        date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    return await run("student_get_my_lessons", dto)


@router.get("/tutors/{tutor_user_id}/lessons")
@require_auth(["student"])
async def get_tutor_lessons(
    tutor_user_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetTutorLessonsDTO(
        access_token=authorization.split(" ")[1],
        tutor_user_id=tutor_user_id,
        date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    return await run("student_get_tutor_lessons", dto)


@router.post("/lessons")
@require_auth(["student"])
async def create_lesson(
    dto: StudentCreateLessonDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_create_lesson", dto)


@router.get("/lessons/{lesson_id}")
@require_auth(["student"])
async def get_lesson(
    lesson_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetLessonDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
    )
    return await run("student_get_lesson", dto)


@router.post("/lessons/{lesson_id}/join")
@require_auth(["student"])
async def join_lesson(
    lesson_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentJoinLessonDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
    )
    return await run("student_join_lesson", dto)


@router.delete("/lessons/{lesson_id}/leave")
@require_auth(["student"])
async def leave_lesson(
    lesson_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentLeaveLessonDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
    )
    return await run("student_leave_lesson", dto)


# === Tutors ===

@router.get("/tutors/{tutor_user_id}/slots")
@require_auth(["student"])
async def get_available_slots(
    tutor_user_id: int,
    date_from: str,
    date_to: str,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetAvailableSlotsDTO(
        access_token=authorization.split(" ")[1],
        tutor_user_id=tutor_user_id,
        date_from=date_from, date_to=date_to,
    )
    return await run("student_get_available_slots", dto)


# === Configurations ===

@router.get("/configurations")
@require_auth(["student"])
async def get_my_configurations(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetMyConfigurationsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit, offset=offset,
    )
    return await run("student_get_my_configurations", dto)


@router.get("/configurations/{config_id}")
@require_auth(["student"])
async def get_configuration(
    config_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetConfigurationDTO(
        access_token=authorization.split(" ")[1],
        config_id=config_id,
    )
    return await run("student_get_configuration", dto)


@router.post("/configurations")
@require_auth(["student"])
async def create_configuration(
    dto: StudentCreateConfigurationDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_create_configuration", dto)


@router.post("/configurations/by-code")
@require_auth(["student"])
async def create_configuration_by_code(
    dto: StudentCreateConfigurationByCodeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_create_configuration_by_code", dto)


@router.delete("/configurations/{config_id}")
@require_auth(["student"])
async def delete_configuration(
    config_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentDeleteConfigurationDTO(
        access_token=authorization.split(" ")[1],
        config_id=config_id,
    )
    return await run("student_delete_configuration", dto)