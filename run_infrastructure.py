"""Event-infra lifecycle. Apply reviewed migrations with python -m scripts.migrate."""
from pathlib import Path
import asyncio
import os

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from infrastructure.config_loader import load_config_from_env
from infrastructure.event_infrastructure import create_pipeline

ROOT = Path(__file__).resolve().parent


def _resolve_sync_db_url(db_url: str, driver: str) -> str:
    scheme, rest = db_url.split("://", 1)
    return f"{scheme}+{driver}://{rest}" if "+" not in scheme else db_url


def migration_config(db_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
    return config


def check_database_schema(db_url: str) -> None:
    """Read-only check: startup never generates or applies migrations."""
    from models import metadata
    heads = set(ScriptDirectory.from_config(migration_config(db_url)).get_heads())
    engine = create_engine(db_url, hide_parameters=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            if set(context.get_current_heads()) != heads:
                raise RuntimeError("Database revision differs; run python -m scripts.migrate")
            if compare_metadata(context, metadata):
                raise RuntimeError("Database schema differs from models; review migrations")
    finally:
        engine.dispose()


async def start_infrastructure(schemas_fn=None):
    config = load_config_from_env(base_dir=ROOT)
    if not config.db_url or not os.getenv("DB_URL"):
        raise RuntimeError("Configure DB_URL and DB_URL_ASYNC in .infra.env")
    sync_url = _resolve_sync_db_url(os.environ["DB_URL"], os.getenv("DB_SYNC_DRIVER", "psycopg"))
    from sqlalchemy.engine import make_url
    sync, asynchronous = make_url(sync_url), make_url(config.db_url)
    if (sync.host, sync.port or 5432, sync.database) != (asynchronous.host, asynchronous.port or 5432, asynchronous.database):
        raise RuntimeError("DB_URL and DB_URL_ASYNC must address the same database")
    await asyncio.to_thread(check_database_schema, sync_url)
    from models import get_all_schemas
    # Custom SQL mutations in scenarios cannot invalidate the infrastructure read cache.
    config.cache.enabled = False
    return await create_pipeline(
        db_url=config.db_url, channels=config.channels,
        schemas=schemas_fn() if schemas_fn else get_all_schemas(),
        exclude_tables={t.strip() for t in os.getenv("EXCLUDE_TABLES", "alembic_version").split(",") if t.strip()},
        pool_recycle=config.pool_recycle, pool_pre_ping=config.pool_pre_ping,
        pool_timeout=config.pool_timeout, default_timeout=config.default_timeout,
        shutdown_timeout=config.shutdown_timeout, max_concurrency=config.max_concurrency,
        metrics_enabled=config.metrics_enabled, retry=config.retry, cache=config.cache,
    )


def _run_tests() -> bool:
    """Preserve the legacy --test entry point using the isolated project suite."""
    import subprocess
    import sys
    environment = os.environ.copy()
    environment["SHAD_RUN_DB_TESTS"] = "1"
    return subprocess.run([sys.executable, "-m", "pytest"], cwd=ROOT, env=environment).returncode == 0


async def _main(run_tests=False):
    if run_tests and not await asyncio.to_thread(_run_tests):
        raise RuntimeError("Project checks failed; infrastructure was not started")
    router = await start_infrastructure()
    try:
        await asyncio.Event().wait()
    finally:
        await router.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Run isolated project checks before starting")
    args = parser.parse_args()
    try:
        asyncio.run(_main(args.test))
    except KeyboardInterrupt:
        pass
