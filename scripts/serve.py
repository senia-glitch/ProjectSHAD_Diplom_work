"""Run the standard HTTP entry point against the selected local database."""
import argparse
import os

from scripts.db_config import select_database


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    select_database(args.test)
    if args.port is not None:
        os.environ["FAT_PORT"] = str(args.port)
    from fastbase import start
    start()
