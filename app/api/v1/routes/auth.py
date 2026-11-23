from fastapi import APIRouter
from core import run

from app.scenarios.auth.login import LoginDTO
from app.scenarios.auth.refresh import RefreshDTO
from app.scenarios.auth.logout import LogoutDTO

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(dto: LoginDTO):
    return await run("login", dto)


@router.post("/refresh")
async def refresh(dto: RefreshDTO):
    return await run("refresh", dto)


@router.post("/logout")
async def logout(dto: LogoutDTO):
    return await run("logout", dto)
