from pydantic import BaseModel
from core import BaseScenario, CoreError, register_scenario


class ReadyResponse(BaseModel):
    status: str = "ready"


@register_scenario("ready", response=ReadyResponse)
class ReadyScenario(BaseScenario):
    async def execute(self, dto=None) -> ReadyResponse:
        try:
            rows = await self._db.query("SELECT 1 AS ready", {})
            if not rows or rows[0].get("ready") != 1:
                raise ValueError("Unexpected database response")
        except Exception:
            raise CoreError("Database is not ready", http_status=503) from None
        return ReadyResponse()
