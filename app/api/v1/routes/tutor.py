from fastapi import APIRouter, Depends, Header, Query
from core import run
from app.api.v1.dependencies import get_current_user, require_auth

from app.scenarios.tutor.profile import TutorGetMyProfileDTO, TutorUpdateMySettingsDTO
from app.scenarios.tutor.lessons import (
    TutorGetMyLessonsDTO, TutorGetLessonDTO, TutorCreateLessonDTO,
    TutorUpdateLessonDTO, TutorDeleteLessonDTO,
)
from app.scenarios.tutor.participants import (
    TutorGetParticipantsDTO, TutorAddParticipantDTO, TutorRemoveParticipantDTO,
    TutorSetPaymentDTO,
)
from app.scenarios.tutor.bookings import (
    TutorGetMyBookingsDTO, TutorCreateBookingDTO,
    TutorUpdateBookingDTO, TutorDeleteBookingDTO,
)
from app.scenarios.tutor.configurations import (
    TutorGetMyConfigurationsDTO, TutorGetConfigurationDTO,
    TutorCreateConfigurationDTO, TutorCreateConfigurationByCodeDTO,
    TutorUpdateConfigurationDTO, TutorResetConfigurationDTO,
    TutorDeleteConfigurationDTO,
)
from app.scenarios.tutor.students import TutorGetStudentBusySlotsDTO, TutorListStudentsDTO
from app.scenarios.tutor.statistics import TutorGetStatisticsDTO
from app.scenarios.tutor.lesson_details import TutorLessonDetailsDTO

router = APIRouter(prefix="/tutor", tags=["tutor"])


# === Profile ===

@router.get("/me")
@require_auth(["tutor"])
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("tutor_get_my_profile", dto)


@router.patch("/me/settings")
@require_auth(["tutor"])
async def update_my_settings(
    dto: TutorUpdateMySettingsDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_update_my_settings", dto)


# === Lessons ===

@router.get("/me/lessons")
@require_auth(["tutor"])
async def get_my_lessons(
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetMyLessonsDTO(
        access_token=authorization.split(" ")[1],
        date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    return await run("tutor_get_my_lessons", dto)


@router.post("/lessons")
@require_auth(["tutor"])
async def create_lesson(
    dto: TutorCreateLessonDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_lesson", dto)


@router.get("/lessons/details")
@require_auth(["tutor"])
async def get_lesson_details(
    date_from: str,
    date_to: str,
    student_ids: str | None = None,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorLessonDetailsDTO(
        access_token=authorization.split(" ")[1],
        date_from=date_from, date_to=date_to, student_ids=student_ids,
    )
    return await run("tutor_lesson_details", dto)


@router.get("/lessons/{lesson_id}")
@require_auth(["tutor"])
async def get_lesson(
    lesson_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetLessonDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
    )
    return await run("tutor_get_lesson", dto)


@router.patch("/lessons/{lesson_id}")
@require_auth(["tutor"])
async def update_lesson(
    lesson_id: int,
    dto: TutorUpdateLessonDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.lesson_id = lesson_id
    return await run("tutor_update_lesson", dto)


@router.delete("/lessons/{lesson_id}")
@require_auth(["tutor"])
async def delete_lesson(
    lesson_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorDeleteLessonDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
    )
    return await run("tutor_delete_lesson", dto)


# === Participants ===

@router.get("/lessons/{lesson_id}/participants")
@require_auth(["tutor"])
async def get_participants(
    lesson_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetParticipantsDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
    )
    return await run("tutor_get_participants", dto)


@router.post("/lessons/{lesson_id}/participants")
@require_auth(["tutor"])
async def add_participant(
    lesson_id: int,
    dto: TutorAddParticipantDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.lesson_id = lesson_id
    return await run("tutor_add_participant", dto)


@router.delete("/lessons/{lesson_id}/participants/{student_user_id}")
@require_auth(["tutor"])
async def remove_participant(
    lesson_id: int,
    student_user_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorRemoveParticipantDTO(
        access_token=authorization.split(" ")[1],
        lesson_id=lesson_id,
        student_user_id=student_user_id,
    )
    return await run("tutor_remove_participant", dto)


@router.patch("/lessons/{lesson_id}/participants/{student_user_id}/payment")
@require_auth(["tutor"])
async def set_participant_payment(
    lesson_id: int,
    student_user_id: int,
    dto: TutorSetPaymentDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.lesson_id = lesson_id
    dto.student_user_id = student_user_id
    return await run("tutor_set_payment", dto)


# === Bookings ===

@router.get("/me/bookings")
@require_auth(["tutor"])
async def get_my_bookings(
    weekday: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetMyBookingsDTO(
        access_token=authorization.split(" ")[1],
        weekday=weekday, limit=limit, offset=offset,
    )
    return await run("tutor_get_my_bookings", dto)


@router.post("/bookings")
@require_auth(["tutor"])
async def create_booking(
    dto: TutorCreateBookingDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_booking", dto)


@router.patch("/bookings/{booking_id}")
@require_auth(["tutor"])
async def update_booking(
    booking_id: int,
    dto: TutorUpdateBookingDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.booking_id = booking_id
    return await run("tutor_update_booking", dto)


@router.delete("/bookings/{booking_id}")
@require_auth(["tutor"])
async def delete_booking(
    booking_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorDeleteBookingDTO(
        access_token=authorization.split(" ")[1],
        booking_id=booking_id,
    )
    return await run("tutor_delete_booking", dto)


# === Configurations ===

@router.get("/configurations")
@require_auth(["tutor"])
async def get_my_configurations(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetMyConfigurationsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit, offset=offset,
    )
    return await run("tutor_get_my_configurations", dto)


@router.get("/configurations/{config_id}")
@require_auth(["tutor"])
async def get_configuration(
    config_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetConfigurationDTO(
        access_token=authorization.split(" ")[1],
        config_id=config_id,
    )
    return await run("tutor_get_configuration", dto)


@router.post("/configurations")
@require_auth(["tutor"])
async def create_configuration(
    dto: TutorCreateConfigurationDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_configuration", dto)


@router.post("/configurations/by-code")
@require_auth(["tutor"])
async def create_configuration_by_code(
    dto: TutorCreateConfigurationByCodeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_configuration_by_code", dto)


@router.patch("/configurations/{config_id}")
@require_auth(["tutor"])
async def update_configuration(
    config_id: int,
    dto: TutorUpdateConfigurationDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.config_id = config_id
    return await run("tutor_update_configuration", dto)


@router.post("/configurations/{config_id}/reset")
@require_auth(["tutor"])
async def reset_configuration(
    config_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorResetConfigurationDTO(
        access_token=authorization.split(" ")[1],
        config_id=config_id,
    )
    return await run("tutor_reset_configuration", dto)


@router.delete("/configurations/{config_id}")
@require_auth(["tutor"])
async def delete_configuration(
    config_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorDeleteConfigurationDTO(
        access_token=authorization.split(" ")[1],
        config_id=config_id,
    )
    return await run("tutor_delete_configuration", dto)


# === Students ===

@router.get("/students")
@require_auth(["tutor"])
async def list_students(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorListStudentsDTO(
        access_token=authorization.split(" ")[1],
    )
    return await run("tutor_list_students", dto)


# === Statistics ===

@router.get("/statistics")
@require_auth(["tutor"])
async def get_statistics(
    year: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    granularity: str | None = None,
    student_ids: str | None = None,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetStatisticsDTO(
        access_token=authorization.split(" ")[1],
        year=year, date_from=date_from, date_to=date_to,
        granularity=granularity, student_ids=student_ids,
    )
    return await run("tutor_get_statistics", dto)


# === Student Busy Slots ===

@router.get("/students/{student_user_id}/busy-slots")
@require_auth(["tutor"])
async def get_student_busy_slots(
    student_user_id: int,
    date_from: str,
    date_to: str,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetStudentBusySlotsDTO(
        access_token=authorization.split(" ")[1],
        student_user_id=student_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return await run("tutor_get_student_busy_slots", dto)