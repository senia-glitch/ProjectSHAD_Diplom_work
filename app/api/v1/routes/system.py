from fastapi import APIRouter, Depends, Header
from core import run
from app.api.v1.dependencies import get_current_user, require_auth

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/init-roles")
@require_auth(["admin"])
async def init_roles(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    return await run("init_roles", None)


@router.get("/stats")
@require_auth(["admin"])
async def get_stats(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    return await run("stats", None)


@router.get("/server-time")
async def server_time():
    return await run("server_time", None)
