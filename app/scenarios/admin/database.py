"""Прямой доступ владельца к БД: таблицы, строки, правка/удаление, SQL-консоль.

Безопасность:
- имена таблиц и столбцов принимаются только из information_schema текущей схемы;
- значения — параметрами с приведением к типу столбца;
- секреты (хэши паролей и ключей, refresh-токены, коды досок) показываются маской и не правятся;
- SQL «чтение» оборачивается в SELECT … LIMIT: изменяющий запрос внутри подзапроса PostgreSQL не выполнит;
- SQL «запись» — только с явным подтверждением, одной командой, в своей транзакции;
- каждое изменение и каждый SQL-запрос пишутся в журнал действий.
"""
import datetime
import decimal
import json
import re
import uuid

from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario

from app.core import blocklist
from app.utils.admin_audit import audit

MASK = "••••••"
SECRET_COLUMNS = {"password_hash", "refresh_token", "key_hash", "code_lookup", "creator_key"}
SECRET_BY_TABLE = {
    "users": {"password_hash", "refresh_token"},
    "admins": {"key_hash"},
    "boards": {"code_lookup", "creator_key"},
}
READ_LIMIT = 500
SORTABLE_TYPES_EXCLUDED = {"json", "jsonb", "bytea"}


def _plain(value):
    """Значение из БД → JSON-совместимое для показа."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} байт>"
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def _row(row: dict, secret: set[str]) -> dict:
    return {k: (MASK if k in secret and v is not None else _plain(v)) for k, v in dict(row).items()}


async def _schema(db) -> dict:
    """{table: {"columns": [{name, type, udt, nullable, default}], "pk": [..]}} текущей схемы."""
    cols = await db.query(
        "SELECT c.table_name, c.column_name, c.data_type, c.udt_name, c.is_nullable, c.column_default "
        "FROM information_schema.columns c JOIN information_schema.tables t "
        "ON t.table_schema = c.table_schema AND t.table_name = c.table_name "
        "WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE' "
        "ORDER BY c.table_name, c.ordinal_position", {})
    pks = await db.query(
        "SELECT tc.table_name, kcu.column_name FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name "
        "AND kcu.table_schema = tc.table_schema "
        "WHERE tc.table_schema = current_schema() AND tc.constraint_type = 'PRIMARY KEY' "
        "ORDER BY kcu.ordinal_position", {})
    schema: dict = {}
    for c in cols:
        schema.setdefault(c["table_name"], {"columns": [], "pk": []})["columns"].append({
            "name": c["column_name"], "type": c["data_type"], "udt": c["udt_name"],
            "nullable": c["is_nullable"] == "YES", "default": c["column_default"],
        })
    for p in pks:
        if p["table_name"] in schema:
            schema[p["table_name"]]["pk"].append(p["column_name"])
    return schema


def _table(schema: dict, name: str) -> dict:
    if name not in schema:
        raise NotFoundError("Table not found")
    return schema[name]


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _cast_type(column: dict) -> str:
    """Тип для CAST: имя udt безопасно — оно из information_schema, массивы — через data_type."""
    udt = column["udt"]
    if udt.startswith("_"):
        return udt[1:] + "[]"
    return udt


class DbActorDTO(BaseModel):
    actor_id: int
    ip: str | None = None


class TableInfo(BaseModel):
    name: str
    rows: int
    columns: list[dict]
    pk: list[str]
    secret_columns: list[str]


class TablesResponse(BaseModel):
    tables: list[TableInfo]


@register_scenario("admin_db_tables", dto=DbActorDTO, response=TablesResponse)
class AdminDbTablesScenario(BaseScenario):
    async def execute(self, dto: DbActorDTO) -> TablesResponse:
        schema = await _schema(self._db)
        tables = []
        for name in sorted(schema):
            count = await self._db.query(f"SELECT COUNT(*) AS n FROM {_q(name)}", {})
            tables.append(TableInfo(
                name=name, rows=int(count[0]["n"]) if count else 0,
                columns=schema[name]["columns"], pk=schema[name]["pk"],
                secret_columns=sorted(SECRET_BY_TABLE.get(name, set())),
            ))
        return TablesResponse(tables=tables)


class RowsDTO(DbActorDTO):
    table: str = Field(min_length=1, max_length=63)
    search: str | None = Field(default=None, max_length=200)
    order_by: str | None = Field(default=None, max_length=63)
    desc: bool = True
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class RowsResponse(BaseModel):
    table: str
    columns: list[dict]
    pk: list[str]
    secret_columns: list[str]
    rows: list[dict]
    total: int


@register_scenario("admin_db_rows", dto=RowsDTO, response=RowsResponse)
class AdminDbRowsScenario(BaseScenario):
    async def execute(self, dto: RowsDTO) -> RowsResponse:
        schema = await _schema(self._db)
        table = _table(schema, dto.table)
        names = {c["name"] for c in table["columns"]}
        order = dto.order_by or (table["pk"][0] if table["pk"] else None)
        if order and order not in names:
            raise ValidationError("Unknown column")
        where, params = "", {"lim": dto.limit, "off": dto.offset}
        if dto.search and dto.search.strip():
            # Поиск по строке целиком (все столбцы как текст).
            where = "WHERE CAST(row_to_json(t) AS text) ILIKE :q"
            params["q"] = f"%{dto.search.strip()}%"
        order_sql = f"ORDER BY {_q(order)} {'DESC' if dto.desc else 'ASC'} NULLS LAST" if order else ""
        rows = await self._db.query(
            f"SELECT * FROM {_q(dto.table)} AS t {where} {order_sql} LIMIT :lim OFFSET :off", params)
        total = await self._db.query(f"SELECT COUNT(*) AS n FROM {_q(dto.table)} AS t {where}", params)
        secret = SECRET_BY_TABLE.get(dto.table, set())
        return RowsResponse(
            table=dto.table, columns=table["columns"], pk=table["pk"], secret_columns=sorted(secret),
            rows=[_row(r, secret) for r in rows], total=int(total[0]["n"]) if total else 0,
        )


class RowChangeDTO(DbActorDTO):
    table: str = Field(min_length=1, max_length=63)
    pk: dict
    values: dict = {}


class RowChangeResponse(BaseModel):
    ok: bool
    row: dict | None = None


def _pk_where(table: dict, pk: dict) -> tuple[str, dict]:
    if not table["pk"]:
        raise ValidationError("Table has no primary key: use the SQL console")
    if set(pk) != set(table["pk"]):
        raise ValidationError("Primary key values required")
    types = {c["name"]: c for c in table["columns"]}
    parts, params = [], {}
    for i, name in enumerate(table["pk"]):
        parts.append(f"{_q(name)} = CAST(CAST(:pk{i} AS text) AS {_cast_type(types[name])})")
        params[f"pk{i}"] = str(pk[name])
    return " AND ".join(parts), params


@register_scenario("admin_db_update_row", dto=RowChangeDTO, response=RowChangeResponse)
class AdminDbUpdateRowScenario(BaseScenario):
    async def execute(self, dto: RowChangeDTO) -> RowChangeResponse:
        schema = await _schema(self._db)
        table = _table(schema, dto.table)
        columns = {c["name"]: c for c in table["columns"]}
        secret = SECRET_BY_TABLE.get(dto.table, set())
        if not dto.values:
            raise ValidationError("Nothing to update")
        sets, params = [], {}
        for i, (name, value) in enumerate(dto.values.items()):
            if name not in columns:
                raise ValidationError(f"Unknown column {name}")
            if name in secret or name in table["pk"]:
                raise ValidationError(f"Column {name} cannot be edited here")
            if value is None:
                sets.append(f"{_q(name)} = NULL")
            else:
                sets.append(f"{_q(name)} = CAST(CAST(:v{i} AS text) AS {_cast_type(columns[name])})")
                is_array = columns[name]["udt"].startswith("_")
                params[f"v{i}"] = _array_literal(value) if is_array and isinstance(value, list) else _text_value(value)
        where, pk_params = _pk_where(table, dto.pk)
        params.update(pk_params)
        try:
            rows = await self._db.query(
                f"UPDATE {_q(dto.table)} SET {', '.join(sets)} WHERE {where} RETURNING *", params, channel="write")
        except Exception as e:  # ошибка типа/ограничения — понятным текстом владельцу
            raise ValidationError(f"Database rejected the change: {_short(e)}")
        if not rows:
            raise NotFoundError("Row not found")
        await audit(self._db, dto.actor_id, "db_update_row", f"{dto.table}:{_pk_text(dto.pk)}",
                    {"columns": sorted(dto.values)}, dto.ip)
        if dto.table == "users":
            await blocklist.load(self._db)
        return RowChangeResponse(ok=True, row=_row(rows[0], secret))


@register_scenario("admin_db_delete_row", dto=RowChangeDTO, response=RowChangeResponse)
class AdminDbDeleteRowScenario(BaseScenario):
    async def execute(self, dto: RowChangeDTO) -> RowChangeResponse:
        schema = await _schema(self._db)
        table = _table(schema, dto.table)
        where, params = _pk_where(table, dto.pk)
        try:
            rows = await self._db.query(
                f"DELETE FROM {_q(dto.table)} WHERE {where} RETURNING *", params, channel="write")
        except Exception as e:
            raise ValidationError(f"Database rejected the change: {_short(e)}")
        if not rows:
            raise NotFoundError("Row not found")
        await audit(self._db, dto.actor_id, "db_delete_row", f"{dto.table}:{_pk_text(dto.pk)}", ip=dto.ip)
        if dto.table == "users":
            await blocklist.load(self._db)
        return RowChangeResponse(ok=True)


def _text_value(value) -> str:
    """Значение формы → текст для CAST к типу столбца."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _array_literal(items: list) -> str:
    """Список из формы → литерал массива PostgreSQL: {"a","b"}; None → NULL."""
    def one(v):
        if v is None:
            return "NULL"
        text = _text_value(v).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{text}"'
    return "{" + ",".join(one(v) for v in items) + "}"


def _pk_text(pk: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(pk.items()))


def _short(error: Exception) -> str:
    lines = str(error).strip().splitlines()
    # Сообщение драйвера: первая строка без технического префикса вида «(sqlalchemy...Error) ».
    first = lines[0] if lines else type(error).__name__
    first = re.sub(r"^\([\w.]+\)\s*", "", first)
    first = re.sub(r"^<class '[\w.]+'>:\s*", "", first)
    return first[:300]


class SqlDTO(DbActorDTO):
    sql: str = Field(min_length=1, max_length=20000)
    # Запись выполняется только с явным подтверждением владельца.
    write: bool = False
    confirm: bool = False


class SqlResponse(BaseModel):
    mode: str
    columns: list[str] = []
    rows: list[dict] = []
    truncated: bool = False
    message: str = ""


def _clean_sql(sql: str) -> str:
    text = sql.strip()
    while text.endswith(";"):
        text = text[:-1].rstrip()
    if not text:
        raise ValidationError("Empty query")
    return text


@register_scenario("admin_db_sql", dto=SqlDTO, response=SqlResponse)
class AdminDbSqlScenario(BaseScenario):
    async def execute(self, dto: SqlDTO) -> SqlResponse:
        sql = _clean_sql(dto.sql)
        if not dto.write:
            try:
                rows = await self._db.query(f"SELECT * FROM ({sql}) AS admin_query LIMIT {READ_LIMIT + 1}", {})
            except Exception as e:
                await audit(self._db, dto.actor_id, "db_sql_read_failed", None, {"sql": sql[:2000]}, dto.ip)
                raise ValidationError(f"Query failed: {_short(e)}")
            await audit(self._db, dto.actor_id, "db_sql_read", None, {"sql": sql[:2000], "rows": len(rows)}, dto.ip)
            columns = list(rows[0].keys()) if rows else []
            secret = {c for c in columns if c in SECRET_COLUMNS}
            return SqlResponse(
                mode="read", columns=columns, rows=[_row(r, secret) for r in rows[:READ_LIMIT]],
                truncated=len(rows) > READ_LIMIT,
                message=f"Строк: {min(len(rows), READ_LIMIT)}{' (показаны первые ' + str(READ_LIMIT) + ')' if len(rows) > READ_LIMIT else ''}",
            )
        if not dto.confirm:
            raise ValidationError("Write queries require explicit confirmation")
        try:
            rows = await self._db.query(sql, {}, channel="write")
        except Exception as e:
            await audit(self._db, dto.actor_id, "db_sql_write_failed", None, {"sql": sql[:2000]}, dto.ip)
            raise ValidationError(f"Query failed: {_short(e)}")
        await audit(self._db, dto.actor_id, "db_sql_write", None, {"sql": sql[:2000]}, dto.ip)
        await blocklist.load(self._db)
        rows = rows or []
        columns = list(rows[0].keys()) if rows else []
        secret = {c for c in columns if c in SECRET_COLUMNS}
        return SqlResponse(
            mode="write", columns=columns, rows=[_row(r, secret) for r in rows[:READ_LIMIT]],
            truncated=len(rows) > READ_LIMIT,
            message="Выполнено" + (f", возвращено строк: {len(rows)}" if rows else ""),
        )
