import asyncio
import logging
from contextlib import asynccontextmanager

from fastbase import make_app, start
from core import run, start_core, shutdown_core
from core.scenario_registry import ScenarioRegistry
from fastapi.routing import iter_route_contexts

from app.api.access import install_access
from app.core.board_settings import board_settings
from app.core.config import AppSettings
from app.realtime.hub import hub
from app.scenarios.boards.boards import CleanupDTO
from app.scenarios.system.lesson_upkeep import LessonUpkeepDTO

logger = logging.getLogger(__name__)
BOARD_CLEANUP_EVERY_SECONDS = 3600
LESSON_UPKEEP_EVERY_SECONDS = 60


async def _board_cleanup_loop():
    """Удаление досок, на которые не заходили BOARD_RETENTION_DAYS дней."""
    while True:
        try:
            removed = await run("boards.cleanup", CleanupDTO(days=board_settings.retention_days))
            if removed.count:
                logger.info("Removed %s abandoned boards", removed.count)
        except Exception:
            logger.exception("Board cleanup failed")
        await asyncio.sleep(BOARD_CLEANUP_EVERY_SECONDS)


async def _lesson_upkeep_loop():
    """Просроченные заявки и уроки во время отпуска/болезни репетитора (раз в минуту)."""
    while True:
        try:
            done = await run("lesson_upkeep", LessonUpkeepDTO())
            if done.expired_requests or done.system_finished:
                logger.info("Lesson upkeep: expired=%s system_finished=%s",
                            done.expired_requests, done.system_finished)
        except Exception:
            logger.exception("Lesson upkeep failed")
        await asyncio.sleep(LESSON_UPKEEP_EVERY_SECONDS)


def build_app():
    settings = AppSettings()
    application = make_app()
    install_access(application, settings)
    actions = {getattr(r.endpoint, "external_action", None)
               for r in iter_route_contexts(application.routes) if r.endpoint is not None}
    expected = set().union(*application.state.access_policy.values())
    missing = {action for action in expected - actions if not action.startswith("service.")}
    if missing:
        raise RuntimeError(f"Missing HTTP actions: {sorted(missing)}")

    @asynccontextmanager
    async def lifespan(app):
        from run_infrastructure import start_infrastructure
        router = await start_infrastructure()
        try:
            await start_core(router=router, discover=settings.core_discover)
            expected = {getattr(r.endpoint, "core_scenario", None)
                        for r in iter_route_contexts(app.routes) if r.endpoint is not None}
            expected.discard(None)
            missing = expected - ScenarioRegistry.list_scenarios().keys()
            if missing:
                raise RuntimeError(f"Missing core scenarios: {sorted(missing)}")
            result = await run("init_roles", None)
            logger.info("Roles initialized: created=%s", result.created)
            blocked = await run("admin_load_blocklist", None)
            logger.info("Blocked users loaded: %s", blocked.count)
            tasks = [asyncio.create_task(hub.autosave_loop(board_settings.autosave_minutes * 60)),
                     asyncio.create_task(_board_cleanup_loop()),
                     asyncio.create_task(_lesson_upkeep_loop())]
            try:
                yield
            finally:
                for task in tasks:
                    task.cancel()
                await hub.shutdown()  # сохранить открытые доски до остановки ядра и БД
        finally:
            try:
                await shutdown_core()
            finally:
                await router.shutdown()

    application.router.lifespan_context = lifespan
    logging.getLogger("core").propagate = False
    return application


app = build_app()


if __name__ == "__main__":
    start()
