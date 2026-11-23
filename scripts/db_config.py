"""Database configuration for maintenance and isolated integration checks."""
import os
from pathlib import Path
from sqlalchemy.engine import make_url
from infrastructure.config_loader import load_config_from_env

ROOT = Path(__file__).resolve().parents[1]


def select_database(test: bool = False) -> str:
    load_config_from_env(base_dir=ROOT)
    from run_infrastructure import _resolve_sync_db_url
    if test:
        work = make_url(os.environ["DB_URL"])
        target = make_url(os.environ["TEST_DB_URL"])
        async_target = make_url(os.environ["TEST_DB_URL_ASYNC"])
        if work.database == target.database:
            raise RuntimeError("Test database must differ from the application database")
        if not target.database or "test" not in target.database.lower():
            raise RuntimeError("Refusing a test database without 'test' in its name")
        if (target.host, target.port or 5432, target.database) != (async_target.host, async_target.port or 5432, async_target.database):
            raise RuntimeError("TEST_DB_URL and TEST_DB_URL_ASYNC differ")
        os.environ["DB_URL"] = os.environ["TEST_DB_URL"]
        os.environ["DB_URL_ASYNC"] = os.environ["TEST_DB_URL_ASYNC"]
    return _resolve_sync_db_url(os.environ["DB_URL"], os.getenv("DB_SYNC_DRIVER", "psycopg"))
