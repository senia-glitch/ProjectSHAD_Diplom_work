import json

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from core import run
from app.api.v1.dependencies import get_current_user, require_auth
from app.scenarios.system.logs import SystemGetLogsDTO
from app.utils.frontend_log import LOG_DIR, LOG_FILE

router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    ts: str
    lvl: str
    cat: str
    msg: str
    data: dict | None = None


class LogBatch(BaseModel):
    logs: list[LogEntry]


@router.post("")
@require_auth()
async def write_logs(
    batch: LogBatch,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for entry in batch.logs:
            record = {
                "ts": entry.ts,
                "lvl": entry.lvl,
                "cat": entry.cat,
                "msg": entry.msg,
            }
            if entry.data is not None:
                record["data"] = entry.data
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "count": len(batch.logs)}


@router.get("")
@require_auth(["admin"])
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