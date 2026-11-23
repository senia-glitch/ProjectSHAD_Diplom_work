from pydantic import BaseModel
from core import BaseScenario, register_scenario

from app.utils.frontend_log import write_log_entries


class LogEntry(BaseModel):
    ts: str
    lvl: str
    cat: str
    msg: str
    data: dict | None = None


class LogBatch(BaseModel):
    logs: list[LogEntry]


class WriteLogsResponse(BaseModel):
    ok: bool = True
    count: int


@register_scenario("system_write_logs", dto=LogBatch, response=WriteLogsResponse)
class WriteLogsScenario(BaseScenario):
    async def execute(self, dto: LogBatch) -> WriteLogsResponse:
        write_log_entries([entry.model_dump(exclude_none=True) for entry in dto.logs])
        return WriteLogsResponse(count=len(dto.logs))
