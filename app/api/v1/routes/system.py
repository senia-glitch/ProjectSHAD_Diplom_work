from core import run
from fastapi import APIRouter, Depends, Header
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.system.init_roles import InitRolesResponse
from app.scenarios.system.server_time import ServerTimeResponse
from app.scenarios.system.stats import StatsResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/init-roles", response_model=InitRolesResponse)
@external_scenario("system.init_roles", core="init_roles")
async def init_roles(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    return await run("init_roles", None)


@router.get("/stats", response_model=StatsResponse)
@external_scenario("system.get_stats", core="stats")
async def get_stats(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    return await run("stats", None)


@router.get("/server-time", response_model=ServerTimeResponse)
@external_scenario("system.server_time", core="server_time")
async def server_time():
    return await run("server_time", None)
