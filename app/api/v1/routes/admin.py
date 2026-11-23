from fastapi import APIRouter, Depends, Header, Query
from core import run
from app.api.v1.dependencies import get_current_user, require_auth

from app.scenarios.admin.profile import AdminGetMyProfileDTO
from app.scenarios.admin.users import (
    AdminListUsersDTO, AdminGetUserByIdDTO, AdminUpdateUserDTO,
)
from app.scenarios.admin.students import AdminListStudentsDTO
from app.scenarios.admin.tutors import AdminListTutorsDTO
from app.scenarios.admin.admins import AdminListAdminsDTO

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me")
@require_auth(["admin"])
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("admin_get_my_profile", dto)


@router.get("/users")
@require_auth(["admin"])
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


@router.get("/users/{user_id}")
@require_auth(["admin"])
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


@router.patch("/users/{user_id}")
@require_auth(["admin"])
async def update_user(
    user_id: int,
    dto: AdminUpdateUserDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.target_user_id = user_id
    return await run("admin_update_user", dto)


@router.get("/students")
@require_auth(["admin"])
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


@router.get("/tutors")
@require_auth(["admin"])
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


@router.get("/admins")
@require_auth(["admin"])
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