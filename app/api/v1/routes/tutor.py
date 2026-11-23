from core import run
from fastapi import APIRouter, Depends, Header, Query
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.tutor.bookings import (
    TutorCreateBookingDTO,
    TutorCreateBookingResponse,
    TutorDeleteBookingDTO,
    TutorDeleteBookingResponse,
    TutorGetMyBookingsDTO,
    TutorGetMyBookingsResponse,
    TutorUpdateBookingDTO,
    TutorUpdateBookingResponse,
)
from app.scenarios.tutor.configurations import (
    TutorCreateConfigurationByCodeDTO,
    TutorCreateConfigurationByCodeResponse,
    TutorCreateConfigurationDTO,
    TutorCreateConfigurationResponse,
    TutorDeleteConfigurationDTO,
    TutorDeleteConfigurationResponse,
    TutorGetConfigurationDTO,
    TutorGetConfigurationResponse,
    TutorGetMyConfigurationsDTO,
    TutorGetMyConfigurationsResponse,
    TutorResetConfigurationDTO,
    TutorResetConfigurationResponse,
    TutorUpdateConfigurationDTO,
    TutorUpdateConfigurationResponse,
)
from app.scenarios.tutor.lesson_details import TutorLessonDetailsDTO, TutorLessonDetailsResponse
from app.scenarios.tutor.lessons import (
    TutorCreateLessonDTO,
    TutorCreateLessonResponse,
    TutorDeleteLessonDTO,
    TutorDeleteLessonResponse,
    TutorGetLessonDTO,
    TutorGetLessonResponse,
    TutorGetMyLessonsDTO,
    TutorGetMyLessonsResponse,
    TutorUpdateLessonDTO,
    TutorUpdateLessonResponse,
)
from app.scenarios.tutor.participants import (
    TutorAddParticipantDTO,
    TutorAddParticipantResponse,
    TutorGetParticipantsDTO,
    TutorGetParticipantsResponse,
    TutorRemoveParticipantDTO,
    TutorRemoveParticipantResponse,
    TutorSetPaymentDTO,
    TutorSetPaymentResponse,
)
from app.scenarios.tutor.profile import (
    TutorGetMyProfileDTO,
    TutorGetMyProfileResponse,
    TutorUpdateMySettingsDTO,
    TutorUpdateMySettingsResponse,
)
from app.scenarios.tutor.statistics import TutorGetStatisticsDTO, TutorGetStatisticsResponse
from app.scenarios.tutor.students import (
    TutorGetStudentBusySlotsDTO,
    TutorGetStudentBusySlotsResponse,
    TutorListStudentsDTO,
    TutorListStudentsResponse,
)

router = APIRouter(prefix="/tutor", tags=["tutor"])


# === Profile ===

@router.get("/me", response_model=TutorGetMyProfileResponse)
@external_scenario("tutor.get_my_profile", core="tutor_get_my_profile")
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("tutor_get_my_profile", dto)


@router.patch("/me/settings", response_model=TutorUpdateMySettingsResponse)
@external_scenario("tutor.update_my_settings", core="tutor_update_my_settings")
async def update_my_settings(
    dto: TutorUpdateMySettingsDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_update_my_settings", dto)


# === Lessons ===

@router.get("/me/lessons", response_model=TutorGetMyLessonsResponse)
@external_scenario("tutor.get_my_lessons", core="tutor_get_my_lessons")
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


@router.post("/lessons", response_model=TutorCreateLessonResponse)
@external_scenario("tutor.create_lesson", core="tutor_create_lesson")
async def create_lesson(
    dto: TutorCreateLessonDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_lesson", dto)


@router.get("/lessons/details", response_model=TutorLessonDetailsResponse)
@external_scenario("tutor.get_lesson_details", core="tutor_lesson_details")
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


@router.get("/lessons/{lesson_id}", response_model=TutorGetLessonResponse)
@external_scenario("tutor.get_lesson", core="tutor_get_lesson")
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


@router.patch("/lessons/{lesson_id}", response_model=TutorUpdateLessonResponse)
@external_scenario("tutor.update_lesson", core="tutor_update_lesson")
async def update_lesson(
    lesson_id: int,
    dto: TutorUpdateLessonDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.lesson_id = lesson_id
    return await run("tutor_update_lesson", dto)


@router.delete("/lessons/{lesson_id}", response_model=TutorDeleteLessonResponse)
@external_scenario("tutor.delete_lesson", core="tutor_delete_lesson")
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

@router.get("/lessons/{lesson_id}/participants", response_model=TutorGetParticipantsResponse)
@external_scenario("tutor.get_participants", core="tutor_get_participants")
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


@router.post("/lessons/{lesson_id}/participants", response_model=TutorAddParticipantResponse)
@external_scenario("tutor.add_participant", core="tutor_add_participant")
async def add_participant(
    lesson_id: int,
    dto: TutorAddParticipantDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.lesson_id = lesson_id
    return await run("tutor_add_participant", dto)


@router.delete("/lessons/{lesson_id}/participants/{student_user_id}", response_model=TutorRemoveParticipantResponse)
@external_scenario("tutor.remove_participant", core="tutor_remove_participant")
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


@router.patch("/lessons/{lesson_id}/participants/{student_user_id}/payment", response_model=TutorSetPaymentResponse)
@external_scenario("tutor.set_participant_payment", core="tutor_set_payment")
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

@router.get("/me/bookings", response_model=TutorGetMyBookingsResponse)
@external_scenario("tutor.get_my_bookings", core="tutor_get_my_bookings")
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


@router.post("/bookings", response_model=TutorCreateBookingResponse)
@external_scenario("tutor.create_booking", core="tutor_create_booking")
async def create_booking(
    dto: TutorCreateBookingDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_booking", dto)


@router.patch("/bookings/{booking_id}", response_model=TutorUpdateBookingResponse)
@external_scenario("tutor.update_booking", core="tutor_update_booking")
async def update_booking(
    booking_id: int,
    dto: TutorUpdateBookingDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.booking_id = booking_id
    return await run("tutor_update_booking", dto)


@router.delete("/bookings/{booking_id}", response_model=TutorDeleteBookingResponse)
@external_scenario("tutor.delete_booking", core="tutor_delete_booking")
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

@router.get("/configurations", response_model=TutorGetMyConfigurationsResponse)
@external_scenario("tutor.get_my_configurations", core="tutor_get_my_configurations")
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


@router.get("/configurations/{config_id}", response_model=TutorGetConfigurationResponse)
@external_scenario("tutor.get_configuration", core="tutor_get_configuration")
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


@router.post("/configurations", response_model=TutorCreateConfigurationResponse)
@external_scenario("tutor.create_configuration", core="tutor_create_configuration")
async def create_configuration(
    dto: TutorCreateConfigurationDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_configuration", dto)


@router.post("/configurations/by-code", response_model=TutorCreateConfigurationByCodeResponse)
@external_scenario("tutor.create_configuration_by_code", core="tutor_create_configuration_by_code")
async def create_configuration_by_code(
    dto: TutorCreateConfigurationByCodeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("tutor_create_configuration_by_code", dto)


@router.patch("/configurations/{config_id}", response_model=TutorUpdateConfigurationResponse)
@external_scenario("tutor.update_configuration", core="tutor_update_configuration")
async def update_configuration(
    config_id: int,
    dto: TutorUpdateConfigurationDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.config_id = config_id
    return await run("tutor_update_configuration", dto)


@router.post("/configurations/{config_id}/reset", response_model=TutorResetConfigurationResponse)
@external_scenario("tutor.reset_configuration", core="tutor_reset_configuration")
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


@router.delete("/configurations/{config_id}", response_model=TutorDeleteConfigurationResponse)
@external_scenario("tutor.delete_configuration", core="tutor_delete_configuration")
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

@router.get("/students", response_model=TutorListStudentsResponse)
@external_scenario("tutor.list_students", core="tutor_list_students")
async def list_students(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = TutorListStudentsDTO(
        access_token=authorization.split(" ")[1],
    )
    return await run("tutor_list_students", dto)


# === Statistics ===

@router.get("/statistics", response_model=TutorGetStatisticsResponse)
@external_scenario("tutor.get_statistics", core="tutor_get_statistics")
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

@router.get("/students/{student_user_id}/busy-slots", response_model=TutorGetStudentBusySlotsResponse)
@external_scenario("tutor.get_student_busy_slots", core="tutor_get_student_busy_slots")
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
