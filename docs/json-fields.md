# JSON-поля: единый способ сериализации

## Почему
Через `event-infra -> asyncpg (raw UPDATE ... $N)` JSON-колонки принимают
только JSON-**строку**. Голый `list/dict` роняет запрос:
`invalid input for query argument $9: []`.
При чтении драйвер может вернуть `list/dict` (SQLAlchemy JSON),
`str` (дважды закодированный JSON) или `None`. Без единого кодека
получаем 500, ошибку валидации Pydantic и баг `x in whitelist`
(поиск подстрокой по `str`).

## Реестр (источник правды)
См. `app/utils/json_codec.py::JSON_FIELDS`:

| Таблица | Поля |
|---|---|
| `tutor_settings` | `self_booking_whitelist: list[int]`, `default_links: list[dict]` |
| `configurations` | `default_links: list[dict]` |
| `bookings` | `access_targets: list[int]`, `booking_metadata: dict` |
| `lessons` | `lesson_settings: dict`, `lesson_links: list[dict]`, `lesson_metadata: dict` |
| `lesson_participants` | `participant_settings: dict`, `participant_metadata: dict` |

Новое JSON-поле: добавить в `JSON_FIELDS` + миграцию. Отдельных
`json.dumps/loads` вне кодека не делать.

## Принципы (строго)
1. DTO и бизнес-логика работают только с Python-объектами (`list/dict/None`).
2. Перед **любым** `self._db.create/update` вызвать
   `serialize_for_db(table, data)`.
3. Сразу после **любого** `self._db.query/read`, вернувшего JSON-колонки,
   вызвать `parse_row(table, row)` / `parse_rows(table, rows)`.
4. `None` = "не задано". `[]`/`{}` = "пусто, но задано". Не путать.
5. Проверки `x in whitelist/targets` — только после `parse_int_list(...)`.
   Никогда не делать `row.get("whitelist") or []` напрямую.
6. Даты/время парсить только через `app/utils/safe_parse.py`
   (`parse_iso_datetime/date/time` -> `ValidationError`, не 500).
7. Запись JSON — одним `create/update`, без паттерна "создал, потом
   вторым запросом дописал JSON".

## Примеры
```python
from app.utils.json_codec import serialize_for_db, parse_row, parse_int_list

# WRITE: один вызов, JSON сериализуется внутри
data = serialize_for_db("tutor_settings", {"hourly_rate": 400.0, "default_links": []})
await self._db.update("tutor_settings", settings_id, data)

# READ: десериализация сразу после query
rows = await self._db.query('SELECT * FROM "tutor_settings" WHERE tutor_id = :tid', {"tid": tid})
s = parse_row("tutor_settings", rows[0])

# CHECK: строго через кодек
whitelist = parse_int_list(s.get("self_booking_whitelist"))
if student_id not in whitelist:
    raise ForbiddenError(...)
```

## Анти-паттерны (запрещены)
- `json.dumps/loads` напрямую в сценариях (кроме `json_codec.py`).
- `serialize_json_fields(...)` — deprecated, остался только для
  совместимости, новый код использует `serialize_for_db(table, ...)`.
- `whitelist = row.get(...) or []` + `in` без `parse_int_list`.
- `datetime.fromisoformat` напрямую в сценариях (только `safe_parse`).
- Пагинация срезом в Python (`rows[offset:offset+limit]`) для списков,
  отображающихся 1:1 на строки таблицы: использовать `LIMIT :lim OFFSET :off`
  в SQL. Исключение — `student_get_my_lessons` (список строится по участиям
  с фильтрами в Python; известный долг).
- Мутации (`INSERT/UPDATE/DELETE`) через `_db.query(...)` без явного
  `channel="write"` (дефолт `query` — read-канал).
