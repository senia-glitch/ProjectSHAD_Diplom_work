import datetime

from pydantic import BaseModel, Field
from core import BaseScenario, ValidationError, register_scenario, tracked_scenario
from core.dto import BaseDTO
from app.utils.frontend_log import read_log_entries


class SystemGetLogsDTO(BaseDTO):
    lvl: str | None = None
    cat: str | None = None
    date: str | None = None
    q: str | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class LogItem(BaseModel):
    ts: str
    lvl: str
    cat: str
    msg: str
    data: dict | None = None


class SystemGetLogsResponse(BaseModel):
    items: list[LogItem]
    total: int


def _matches(row: dict, dto: SystemGetLogsDTO, needle: str | None) -> bool:
    if dto.lvl and str(row.get("lvl", "")).lower() != dto.lvl.lower():
        return False
    if dto.cat and str(row.get("cat", "")).lower() != dto.cat.lower():
        return False
    ts = str(row.get("ts", ""))
    if dto.date and not ts.startswith(dto.date):
        return False
    if needle and needle not in str(row.get("msg", "")).lower():
        return False
    return True


@register_scenario("system_get_logs", dto=SystemGetLogsDTO, response=SystemGetLogsResponse)
@tracked_scenario("system_get_logs")
class SystemGetLogsScenario(BaseScenario):
    async def execute(self, dto: SystemGetLogsDTO) -> SystemGetLogsResponse:
        if dto.date is not None:
            try:
                datetime.date.fromisoformat(dto.date)
            except ValueError:
                raise ValidationError("date must be in YYYY-MM-DD format")

        needle = dto.q.strip().lower() if dto.q else None
        matched = [r for r in read_log_entries() if _matches(r, dto, needle)]
        page = matched[dto.offset:dto.offset + dto.limit]

        return SystemGetLogsResponse(
            items=[LogItem(
                ts=str(r.get("ts", "")),
                lvl=str(r.get("lvl", "")),
                cat=str(r.get("cat", "")),
                msg=str(r.get("msg", "")),
                data=r.get("data") if isinstance(r.get("data"), dict) else None,
            ) for r in page],
            total=len(matched),
        )
