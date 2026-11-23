from fastapi import APIRouter, Depends, Header
from core import run
from app.api.v1.dependencies import get_current_user, require_auth

from app.scenarios.users.register import RegisterUserDTO
from app.scenarios.users.get_me import GetMeDTO
from app.scenarios.users.update_me import UpdateMeDTO
from app.scenarios.users.change_password import ChangePasswordDTO
from app.scenarios.users.delete_me import DeleteMeDTO

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
async def register_user(dto: RegisterUserDTO):
    return await run("register", dto)


@router.get("/me")
@require_auth()
async def get_me(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = GetMeDTO(access_token=authorization.split(" ")[1])
    return await run("get_me", dto)


@router.patch("/me")
@require_auth()
async def update_me(
    dto: UpdateMeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("update_me", dto)


@router.post("/me/change-password")
@require_auth()
async def change_password(
    dto: ChangePasswordDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("change_password", dto)


@router.post("/me/delete")
@require_auth()
async def delete_me(
    dto: DeleteMeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("delete_me", dto)
