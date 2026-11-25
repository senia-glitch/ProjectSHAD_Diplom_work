from core import run
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from app.api.access import external_scenario
from app.scenarios.auth.login import LoginDTO, LoginResponse
from app.scenarios.auth.logout import LogoutDTO, LogoutResponse
from app.scenarios.auth.refresh import RefreshDTO, RefreshResponse
from app.scenarios.admin.panel import AdminKeyLoginDTO, AdminKeyLoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@external_scenario("auth.login", core="login")
async def login(dto: LoginDTO):
    return await run("login", dto)


@router.post("/refresh", response_model=RefreshResponse)
@external_scenario("auth.refresh", core="refresh")
async def refresh(dto: RefreshDTO):
    return await run("refresh", dto)


@router.post("/logout", response_model=LogoutResponse)
@external_scenario("auth.logout", core="logout")
async def logout(dto: LogoutDTO):
    return await run("logout", dto)



class AdminKeyBody(BaseModel):
    key: str = Field(min_length=10, max_length=200)


@router.post("/admin-key", response_model=AdminKeyLoginResponse)
@external_scenario("auth.admin_key_login", core="admin_key_login")
async def admin_key_login(request: Request, body: AdminKeyBody):
    """Вход владельца по уникальному ключу (страница /admin/login)."""
    ip = request.client.host if request.client else None
    return await run("admin_key_login", AdminKeyLoginDTO(key=body.key, ip=ip))
