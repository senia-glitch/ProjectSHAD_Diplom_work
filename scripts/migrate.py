"""Apply only committed, reviewed revisions; never autogenerate on startup."""
import argparse
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from scripts.db_config import select_database
from run_infrastructure import migration_config, check_database_schema


def migrate(test=False):
    url = select_database(test)
    config = migration_config(url)
    from models import metadata
    engine = create_engine(url, hide_parameters=True)
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            unexpected = tables - set(metadata.tables) - {"alembic_version"}
            if unexpected:
                raise RuntimeError("Database contains tables outside this project")
            heads = MigrationContext.configure(connection).get_current_heads()
            if tables and not heads:
                raise RuntimeError("Existing data has no migration revision; review before migrating")
            revisions = {r.revision for r in ScriptDirectory.from_config(config).walk_revisions()}
            if set(heads) - revisions:
                raise RuntimeError("Database has an unknown migration revision")
    finally:
        engine.dispose()
    command.upgrade(config, "head")
    check_database_schema(url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    migrate(args.test)
    print("Reviewed migrations applied; schema matches models")
