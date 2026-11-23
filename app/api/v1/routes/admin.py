from core import run
from fastapi import APIRouter, Depends, Header, Query
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.admin.admins import AdminListAdminsDTO, AdminListAdminsResponse
from app.scenarios.admin.profile import AdminGetMyProfileDTO, AdminGetMyProfileResponse
from app.scenarios.admin.students import AdminListStudentsDTO, AdminListStudentsResponse
from app.scenarios.admin.tutors import AdminListTutorsDTO, AdminListTutorsResponse
from app.scenarios.admin.users import (
    AdminGetUserByIdDTO,
    AdminGetUserByIdResponse,
    AdminListUsersDTO,
    AdminListUsersResponse,
    AdminUpdateUserDTO,
    AdminUpdateUserResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=AdminGetMyProfileResponse)
@external_scenario("admin.get_my_profile", core="admin_get_my_profile")
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("admin_get_my_profile", dto)


@router.get("/users", response_model=AdminListUsersResponse)
@external_scenario("admin.list_users", core="admin_list_users")
async def list_users(
    role: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListUsersDTO(
        access_token=authorization.split(" ")[1],
        role=role,
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_users", dto)


@router.get("/users/{user_id}", response_model=AdminGetUserByIdResponse)
@external_scenario("admin.get_user_by_id", core="admin_get_user_by_id")
async def get_user_by_id(
    user_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminGetUserByIdDTO(
        access_token=authorization.split(" ")[1],
        target_user_id=user_id,
    )
    return await run("admin_get_user_by_id", dto)


@router.patch("/users/{user_id}", response_model=AdminUpdateUserResponse)
@external_scenario("admin.update_user", core="admin_update_user")
async def update_user(
    user_id: int,
    dto: AdminUpdateUserDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.target_user_id = user_id
    return await run("admin_update_user", dto)


@router.get("/students", response_model=AdminListStudentsResponse)
@external_scenario("admin.list_students", core="admin_list_students")
async def list_students(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListStudentsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_students", dto)


@router.get("/tutors", response_model=AdminListTutorsResponse)
@external_scenario("admin.list_tutors", core="admin_list_tutors")
async def list_tutors(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListTutorsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_tutors", dto)


@router.get("/admins", response_model=AdminListAdminsResponse)
@external_scenario("admin.list_admins", core="admin_list_admins")
async def list_admins(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListAdminsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_admins", dto)
