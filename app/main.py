import logging
from contextlib import asynccontextmanager

from fastbase import make_app, start
from core import run, start_core, shutdown_core
from core.scenario_registry import ScenarioRegistry
from fastapi.routing import iter_route_contexts

from app.api.access import install_access
from app.core.config import AppSettings

logger = logging.getLogger(__name__)


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
            yield
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
