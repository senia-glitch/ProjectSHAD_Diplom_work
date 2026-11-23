#!/bin/sh
set -eu
if [ -z "${POSTGRES_TEST_DB:-}" ] || [ "$POSTGRES_TEST_DB" = "$POSTGRES_DB" ]; then
    echo "POSTGRES_TEST_DB must be set and differ from POSTGRES_DB" >&2
    exit 1
fi
case "$POSTGRES_TEST_DB" in
    *[Tt][Ee][Ss][Tt]*) ;;
    *) echo "The isolated test database name must contain test" >&2; exit 1 ;;
esac
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set ON_ERROR_STOP=1 --set test_db="$POSTGRES_TEST_DB" <<'SQL'
SELECT format('CREATE DATABASE %I', :'test_db')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'test_db')
\gexec
SQL
