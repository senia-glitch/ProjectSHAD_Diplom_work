import logging
from contextlib import asynccontextmanager

from fastbase import make_app, start
from core import run


logger = logging.getLogger(__name__)


original_lifespan = None


@asynccontextmanager
async def lifespan(app):
    original_lifespan_ctx = original_lifespan(app)
    async with original_lifespan_ctx as state:
        try:
            result = await run("init_roles", None)
            logger.info("Roles init: created=%s already_exist=%s", result.created, result.already_exist)
        except Exception as e:
            logger.error("Failed to init roles on startup: %s", e)
        yield state


app = make_app()
original_lifespan = app.router.lifespan_context
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    start()
