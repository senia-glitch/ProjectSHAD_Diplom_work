import datetime
from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario


class ServerTimeResponse(BaseModel):
    datetime: str
    offset_hours: float
    utc_datetime: str


@register_scenario("server_time")
@tracked_scenario("server_time")
class ServerTimeScenario(BaseScenario):
    async def execute(self, dto=None) -> ServerTimeResponse:
        now = datetime.datetime.now()
        utc_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        offset_seconds = (now - utc_now).total_seconds()
        offset_hours = round(offset_seconds / 3600, 1)
        return ServerTimeResponse(
            datetime=now.isoformat(),
            offset_hours=offset_hours,
            utc_datetime=utc_now.isoformat(),
        )
