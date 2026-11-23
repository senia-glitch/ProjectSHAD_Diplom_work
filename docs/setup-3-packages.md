# Установка и запуск связки: event-infra + core-package + fastbase

## Требования

- Python **3.11+**
- PostgreSQL **9.6+**, БД создана заранее:
  ```bash
  psql -U postgres -c "CREATE DATABASE my_project;"
  ```
- Git

---

## Шаг 1. Виртуальное окружение

```bash
mkdir my_project && cd my_project
python -m venv venv
```

Активировать:
```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

---

## Шаг 2. Установка трёх пакетов

Одна команда ставит `fastbase` + `core-package` + `event-infra`:

```bash
pip install "fastbase[full] @ git+https://github.com/senia-glitch/fastapi-transport.git"
```

Проверка: `fb version` → `0.2.0`.

---

## Шаг 3. Инициализация

Три команды, **в корне проекта**, по порядку:

```bash
fb init                       # app/, .env.fastbase, docs/, pyproject.toml
infra-init                    # models.py, .infra.env, alembic/, run_infrastructure.py
core-init --target-dir app    # app/scenarios/, app/interfaces/, app/utils/
```

Структура после:
```
my_project/
├── app/
│   ├── main.py              ← точка входа
│   ├── api/v1/routes/       ← роуты (health.py создан)
│   ├── scenarios/           ← сценарии (пусто)
│   ├── core/config.py       ← свои настройки
│   └── schemas/
├── models.py                ← SQLModel-модели (демо: User, Post)
├── alembic/
├── run_infrastructure.py
├── .env.fastbase
├── .infra.env
├── .core-package.env
└── docs/
```

---

## Шаг 4. Правка конфигов

### `.env.fastbase`
```env
FAT_INTEGRATIONS=core,event-infra
FAT_CORE_DISCOVER=app.scenarios
```

### `.infra.env`
```env
DB_URL=postgresql+psycopg://postgres:123@localhost:5432/my_project
DB_URL_ASYNC=postgresql+asyncpg://postgres:123@localhost:5432/my_project

# для разработки достаточно
READ_POOL_SIZE=5
WRITE_POOL_SIZE=5
ADMIN_POOL_SIZE=1
```

---

## Шаг 5. Запуск

```bash
python -m app.main
```

При старте автоматически:
1. `event-infra` применяет миграции из `models.py`.
2. `core-package` поднимает ядро и загружает сценарии из `app.scenarios`.
3. `fastbase` собирает FastAPI, монтирует роуты, запускает uvicorn.

Остановка — `Ctrl+C`.

---

## Проверка работоспособности

Пакеты можно запустить «пустыми» — сервер поднимется, но проверить связку HTTP → core → event-infra → БД не получится. Для этого нужны **хотя бы один сценарий и один роут**.

### Что должно быть в логе при старте

```
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

Плюс строки от event-infra:
```
Конфигурация загружена: каналы=['read', 'write', 'admin']
Схема актуальна, изменений нет        ← либо: Обнаружены изменения, создаём миграцию
Диспетчер 'read': запущено N воркеров
Оркестратор запущен с 3 каналами
Зарегистрировано N сущностей: ...
Integrations started.
```

Если этих строк нет — стек не собрался. Обычно причина — пустой `FAT_INTEGRATIONS` в `.env.fastbase` или неверный `DB_URL_ASYNC`.

### Где живут роуты

- Все роуты монтируются под префиксом `FAT_API_PREFIX` (по умолчанию `/api/v1`).
- **Корневого роута `/` нет** — `GET /` вернёт 404. Это by design.
- Роуты сканируются из пакета `FAT_ROUTES_PACKAGE` (`app.api.v1.routes`). В каждом модуле ищется атрибут `router: APIRouter`.
- Модуль без `router` игнорируется. Модуль с именем на `_` — игнорируется.
- Если ни один роут не найден — монтируется только `health_router`.
- `fb init` создаёт `health.py`, поэтому `/api/v1/health` работает из коробки.

### Проверочные URL

| URL | Ожидание |
|---|---|
| `http://127.0.0.1:8000/docs` | Swagger UI |
| `http://127.0.0.1:8000/api/v1/health` | `{"status":"ok"}` |
| `http://127.0.0.1:8000/api/v1/definitely-not-a-route` | 404 в конверте fastbase: `{"success":false,"error":{"code":3001,...}}` |
| `http://127.0.0.1:8000/` | 404 (корневого роута нет) |

### Тест сквозного пути (рекомендуется)

1. **Сценарий** — `app/scenarios/create_user.py`:

```python
from pydantic import BaseModel
from core import BaseScenario, register_scenario


class CreateUserDTO(BaseModel):
    username: str
    email: str


@register_scenario("create_user")
class CreateUserScenario(BaseScenario):
    async def execute(self, dto: CreateUserDTO):
        user = await self._db.create("users", {
            "username": dto.username,
            "email": dto.email,
        })
        return {"user_id": user["id"], "username": user["username"]}
```

2. **Роут** — `app/api/v1/routes/users.py`:

```python
from fastapi import APIRouter
from core import run
from app.scenarios.create_user import CreateUserDTO

router = APIRouter(tags=["users"])


@router.post("/users")
async def create_user(dto: CreateUserDTO):
    return await run("create_user", dto)
```

3. **Перезапуск** `python -m app.main` и POST на `/api/v1/users` через `/docs`.

Если запись появилась в БД (`psql -d my_project -c "SELECT * FROM users;"`) — связка работает полностью.

### Диагностика

```bash
fb check           # конфиг и структура проекта
infra validate     # конфиг и подключение к БД
```

Обе команды должны выдать только `ok` / `[OK]`, без `fail`.

---

## Основные команды

### fastbase (`fb`)

| Команда | Что делает |
|---|---|
| `fb init [--path app] [--force]` | Создать `app/`, `.env.fastbase`, `docs/` |
| `fb check` | Проверить проект |
| `fb version` | Версия пакета |
| `fb help` | Справка |

### event-infra (`infra-*`)

| Команда | Что делает |
|---|---|
| `infra-init [-y] [--force]` | Создать `models.py`, `.infra.env`, `alembic/`, `run_infrastructure.py` |
| `infra validate` | Проверить конфиг и БД |
| `infra monitor [интервал]` | Мониторинг запущенного приложения |
| `infra reset <db_url> [-y]` | Сбросить БД и миграции |
| `infra test [-v]` | Тесты пакета |
| `infra cheat` | Шпаргалка |

### core-package

| Команда | Что делает |
|---|---|
| `core-init [--target-dir <путь>] [--force]` | Создать `scenarios/`, `interfaces/`, `utils/` |

---

## Ежедневный workflow

- Добавил модель в `models.py` → перезапустил приложение → миграция создалась.
- Добавил файл в `app/scenarios/` с `@register_scenario("...")` → подхватится при старте.
- Добавил файл в `app/api/v1/routes/` с `router = APIRouter()` → подхватится при старте.

Никаких ручных `alembic revision` и регистрации роутов. Единственное правило: **добавил файл — перезапустил приложение**.

---

## Типичные ошибки

| Симптом | Причина | Решение |
|---|---|---|
| `ImportError: fastbase requires core-package` | Установлен только `fastbase` | `pip install "fastbase[full]"` |
| `Scenario 'x' not registered` | `FAT_CORE_DISCOVER` пуст или не тот | Проверить `.env.fastbase` |
| 404 на свой роут | В модуле нет атрибута `router` | `router = APIRouter()` |
| 404 на `/` | Норма — корневого роута нет | Обращаться к `/api/v1/...` |
| Миграции не применяются | Неверный `DB_URL` | `infra validate` |
| Ошибки core отдаются как 500 | Не включён `FAT_INTEGRATIONS` | `FAT_INTEGRATIONS=core,event-infra` |
| `start_core() уже запущено` | Повторный запуск в одном процессе | Для тестов — `reset_core()` |