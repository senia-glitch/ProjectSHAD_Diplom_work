from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario


class ChannelStats(BaseModel):
    active_workers: int
    pool_size: int
    queue_size: int
    tasks_processed: int
    tasks_failed: int
    avg_time_ms: float


class StatsResponse(BaseModel):
    uptime_seconds: float
    total_processed: int
    total_failed: int
    total_queued: int
    is_accepting: bool
    cache_size: int
    channels: dict[str, ChannelStats]


@register_scenario("stats", response=StatsResponse)
@tracked_scenario("stats")
class StatsScenario(BaseScenario):
    async def execute(self, dto=None) -> StatsResponse:
        router = self._db._router
        metrics = router.get_metrics()

        channels = {}
        for name, ch in metrics.channels.items():
            channels[name] = ChannelStats(
                active_workers=ch.active_workers,
                pool_size=ch.pool_size,
                queue_size=ch.queue_size,
                tasks_processed=ch.tasks_processed,
                tasks_failed=ch.tasks_failed,
                avg_time_ms=ch.avg_time_ms,
            )

        return StatsResponse(
            uptime_seconds=metrics.uptime_seconds,
            total_processed=metrics.total_processed,
            total_failed=metrics.total_failed,
            total_queued=metrics.total_queued,
            is_accepting=metrics.is_accepting,
            cache_size=router._cache.size if hasattr(router, "_cache") and router._cache else 0,
            channels=channels,
        )
