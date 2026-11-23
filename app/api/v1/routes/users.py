from core import run
from fastapi import APIRouter, Depends, Header
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.users.change_password import ChangePasswordDTO, ChangePasswordResponse
from app.scenarios.users.delete_me import DeleteMeDTO, DeleteMeResponse
from app.scenarios.users.get_me import GetMeDTO, GetMeResponse
from app.scenarios.users.register import RegisterUserDTO, RegisterUserResponse
from app.scenarios.users.update_me import UpdateMeDTO, UpdateMeResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=RegisterUserResponse)
@external_scenario("users.register_user", core="register")
async def register_user(dto: RegisterUserDTO):
    return await run("register", dto)


@router.get("/me", response_model=GetMeResponse)
@external_scenario("users.get_me", core="get_me")
async def get_me(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = GetMeDTO(access_token=authorization.split(" ")[1])
    return await run("get_me", dto)


@router.patch("/me", response_model=UpdateMeResponse)
@external_scenario("users.update_me", core="update_me")
async def update_me(
    dto: UpdateMeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("update_me", dto)


@router.post("/me/change-password", response_model=ChangePasswordResponse)
@external_scenario("users.change_password", core="change_password")
async def change_password(
    dto: ChangePasswordDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("change_password", dto)


@router.post("/me/delete", response_model=DeleteMeResponse)
@external_scenario("users.delete_me", core="delete_me")
async def delete_me(
    dto: DeleteMeDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    return await run("delete_me", dto)
