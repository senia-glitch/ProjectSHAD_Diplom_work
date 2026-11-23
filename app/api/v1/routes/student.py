from core import run
from fastapi import APIRouter, Depends, Header, Query
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.student.configurations import (
    StudentCreateConfigurationByCodeDTO,
    StudentCreateConfigurationByCodeResponse,
    StudentCreateConfigurationDTO,
    StudentCreateConfigurationResponse,
    StudentDeleteConfigurationDTO,
    StudentDeleteConfigurationResponse,
    StudentGetConfigurationDTO,
    StudentGetConfigurationResponse,
    StudentGetMyConfigurationsDTO,
    StudentGetMyConfigurationsResponse,
)
from app.scenarios.student.lessons import (
    StudentCreateLessonDTO,
    StudentCreateLessonResponse,
    StudentGetLessonDTO,
    StudentGetLessonResponse,
    StudentGetMyLessonsDTO,
    StudentGetMyLessonsResponse,
    StudentGetTutorLessonsDTO,
    StudentGetTutorLessonsResponse,
    StudentJoinLessonDTO,
    StudentJoinLessonResponse,
    StudentLeaveLessonDTO,
    StudentLeaveLessonResponse,
)
from app.scenarios.student.profile import (
    StudentGetMyProfileDTO,
    StudentGetMyProfileResponse,
    StudentUpdateMySettingsDTO,
    StudentUpdateMySettingsResponse,
)
from app.scenarios.student.tutors import StudentGetAvailableSlotsDTO, StudentGetAvailableSlotsResponse

router = APIRouter(prefix="/student", tags=["student"])


# === Profile ===

@router.get("/me", response_model=StudentGetMyProfileResponse)
@external_scenario("student.get_my_profile", core="student_get_my_profile")
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = StudentGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("student_get_my_profile", dto)


@router.patch("/me/settings", response_model=StudentUpdateMySettingsResponse)
@external_scenario("student.update_my_settings", core="student_update_my_settings")
async def update_my_settings(
    dto: StudentUpdateMySettingsDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_update_my_settings", dto)


# === Lessons ===

@router.get("/me/lessons", response_model=StudentGetMyLessonsResponse)
@external_scenario("student.get_my_lessons", core="student_get_my_lessons")
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


@router.get("/tutors/{tutor_user_id}/lessons", response_model=StudentGetTutorLessonsResponse)
@external_scenario("student.get_tutor_lessons", core="student_get_tutor_lessons")
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


@router.post("/lessons", response_model=StudentCreateLessonResponse)
@external_scenario("student.create_lesson", core="student_create_lesson")
async def create_lesson(
    dto: StudentCreateLessonDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_create_lesson", dto)


@router.get("/lessons/{lesson_id}", response_model=StudentGetLessonResponse)
@external_scenario("student.get_lesson", core="student_get_lesson")
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


@router.post("/lessons/{lesson_id}/join", response_model=StudentJoinLessonResponse)
@external_scenario("student.join_lesson", core="student_join_lesson")
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


@router.delete("/lessons/{lesson_id}/leave", response_model=StudentLeaveLessonResponse)
@external_scenario("student.leave_lesson", core="student_leave_lesson")
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

@router.get("/tutors/{tutor_user_id}/slots", response_model=StudentGetAvailableSlotsResponse)
@external_scenario("student.get_available_slots", core="student_get_available_slots")
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

@router.get("/configurations", response_model=StudentGetMyConfigurationsResponse)
@external_scenario("student.get_my_configurations", core="student_get_my_configurations")
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


@router.get("/configurations/{config_id}", response_model=StudentGetConfigurationResponse)
@external_scenario("student.get_configuration", core="student_get_configuration")
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


@router.post("/configurations", response_model=StudentCreateConfigurationResponse)
@external_scenario("student.create_configuration", core="student_create_configuration")
async def create_configuration(
    dto: StudentCreateConfigurationDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_create_configuration", dto)


@router.post("/configurations/by-code", response_model=StudentCreateConfigurationByCodeResponse)
@external_scenario("student.create_configuration_by_code", core="student_create_configuration_by_code")
async def create_configuration_by_code(
    dto: StudentCreateConfigurationByCodeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("student_create_configuration_by_code", dto)


@router.delete("/configurations/{config_id}", response_model=StudentDeleteConfigurationResponse)
@external_scenario("student.delete_configuration", core="student_delete_configuration")
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
