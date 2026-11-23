"""Empty and populated schema transitions in databases created by this test."""
from datetime import datetime
import os
import secrets

import pytest

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.getenv("SHAD_RUN_DB_TESTS") != "1", reason="Set SHAD_RUN_DB_TESTS=1")]


@pytest.mark.parametrize("legacy_naive", [False, True])
def test_migration_preserves_rows_and_server_wall_time(legacy_naive):
    # Read config without changing DB_URL: these tests precede the HTTP lifespan.
    from scripts.db_config import ROOT
    from infrastructure.config_loader import load_config_from_env
    from sqlalchemy.engine import make_url
    import psycopg
    from psycopg import sql
    from sqlalchemy import create_engine, text, inspect
    from alembic import command
    from run_infrastructure import migration_config, check_database_schema

    load_config_from_env(base_dir=ROOT)
    work, test = make_url(os.environ["DB_URL"]), make_url(os.environ["TEST_DB_URL"])
    assert work.database != test.database
    assert "test" in test.database.lower()
    name = "shad_migration_test_" + secrets.token_hex(6)
    dsn = test.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(dsn, autocommit=True) as maintenance:
        maintenance.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        engine = create_engine(test.set(database=name, drivername="postgresql+psycopg"), hide_parameters=True)
        try:
            config = migration_config(engine.url.render_as_string(hide_password=False))
            command.upgrade(config, "35a2d259c8b6")
            if legacy_naive:
                # Older installations may already store server-local TIMESTAMP without TZ.
                with engine.begin() as connection:
                    for table in inspect(connection).get_table_names():
                        for column in inspect(connection).get_columns(table):
                            if getattr(column["type"], "timezone", False):
                                connection.exec_driver_sql(f'ALTER TABLE "{table}" ALTER COLUMN "{column["name"]}" TYPE timestamp without time zone USING "{column["name"]}" AT TIME ZONE current_setting(\'TIMEZONE\')')
            with engine.begin() as connection:
                role_id = connection.execute(text("INSERT INTO roles(name) VALUES ('student') RETURNING id")).scalar_one()
                connection.execute(text('''INSERT INTO users
                    (role_id,username,personal_number,password_hash,full_name,email,created_at)
                    VALUES (:role,'migration-test','TEST-MIGRATION','fixture','Migration','migration@example.test',
                            '2026-11-24 09:30:00')'''), {"role": role_id})
                user_id = connection.execute(text("SELECT id FROM users WHERE username='migration-test'")).scalar_one()
                connection.execute(text("INSERT INTO students(user_id) VALUES (:uid)"), {"uid": user_id})
            command.upgrade(config, "head")
            check_database_schema(engine.url.render_as_string(hide_password=False))
            with engine.connect() as connection:
                row = connection.execute(text("SELECT u.id,u.created_at,s.user_id FROM users u JOIN students s ON s.user_id=u.id")).one()
                assert row == (user_id, datetime(2026, 11, 24, 9, 30), user_id)
            # Reapplying the committed migration is idempotent.
            command.upgrade(config, "head")
        finally:
            engine.dispose()
            maintenance.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
