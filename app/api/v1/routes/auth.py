from core import run
from fastapi import APIRouter
from app.api.access import external_scenario
from app.scenarios.auth.login import LoginDTO, LoginResponse
from app.scenarios.auth.logout import LogoutDTO, LogoutResponse
from app.scenarios.auth.refresh import RefreshDTO, RefreshResponse

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
