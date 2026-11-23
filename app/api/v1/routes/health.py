from core import run
from fastapi import APIRouter
from pydantic import BaseModel
from app.api.access import external_scenario
from app.scenarios.system.ready import ReadyResponse

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"


@router.get("/health", response_model=HealthResponse)
@external_scenario("service.health")
async def health():
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse)
@external_scenario("service.ready", core="ready")
async def ready():
    return await run("ready", None)
