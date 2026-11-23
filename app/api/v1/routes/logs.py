from core import run
from fastapi import APIRouter, Depends, Header, Query
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.system.logs import SystemGetLogsDTO, SystemGetLogsResponse
from app.scenarios.system.write_logs import LogBatch, WriteLogsResponse

router = APIRouter(prefix="/logs", tags=["logs"])



@router.post("", response_model=WriteLogsResponse)
@external_scenario("logs.write_logs", core="system_write_logs")
async def write_logs(
    batch: LogBatch,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    return await run("system_write_logs", batch)


@router.get("", response_model=SystemGetLogsResponse)
@external_scenario("logs.read_logs", core="system_get_logs")
async def read_logs(
    lvl: str | None = None,
    cat: str | None = None,
    date: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = SystemGetLogsDTO(
        access_token=authorization.split(" ")[1],
        lvl=lvl, cat=cat, date=date, q=q,
        limit=limit, offset=offset,
    )
    return await run("system_get_logs", dto)
