# SHAD Tutoring / OpenFullStackTest

Сервис расписания занятий: репетиторы, ученики, брони, уроки, учёт оплат,
уведомления и статистика. Backend: **event-infra + core-package + fastbase + PostgreSQL**.
Frontend: Vue 3 / Vite / Pinia; существующие интерфейс и контракты сохранены.

## Запуск существующей рабочей копии

Из корня проекта, PowerShell:

```powershell
.\venv\Scripts\python.exe -m scripts.migrate
.\venv\Scripts\python.exe -m app.main
```

Миграции применяются отдельной командой. Старт приложения проверяет схему
и ревизию без изменения БД. Настройки подключения остаются в `.infra.env`,
JWT — в `.core-package.env`, HTTP — в `.env.fastbase`.

В другом терминале:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend: [localhost:3000](http://localhost:3000/),
API: [localhost:8000/docs](http://localhost:8000/docs),
готовность HTTP → core → PostgreSQL: [localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready).

## Установка в новую рабочую копию

Проверенный профиль: Python 3.14.6, PostgreSQL 17.5, три пакета стека 0.3.0
на закреплённых Git-коммитах. Полный порядок — [docs/setup-3-packages.md](docs/setup-3-packages.md).

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.lock
.\venv\Scripts\python.exe -m scripts.configure
```

Заполнить подключения в `.infra.env`, создать отдельные основную и тестовую БД,
затем выполнить команды запуска выше. `scripts.configure` создаёт только
отсутствующие настройки и генерирует локальный JWT-секрет.

## Проверки

```powershell
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe -m pip check
.\venv\Scripts\python.exe -m fastbase.cli check

# Интеграция на отдельной TEST_DB_URL, включая проверку миграций.
# Для миграционных тестов пользователь PostgreSQL должен иметь CREATEDB.
$env:SHAD_RUN_DB_TESTS = '1'
.\venv\Scripts\python.exe -m pytest
Remove-Item Env:SHAD_RUN_DB_TESTS

cd frontend
npm test
npm run build
```

Без `SHAD_RUN_DB_TESTS` три проверки PostgreSQL пропускаются явно.
Интеграционный прогон создаёт собственные записи в тестовой БД и удаляет их
после проверки; рабочая БД не используется. Проверка миграций создаёт и удаляет
свои временные БД с префиксом `shad_migration_test_`.

## Документация

- [Карта адаптации и результаты проверок](docs/stack-adaptation.md)
- [Архитектура, правила и назначение проекта](PROJECT.md)
- [Спецификация](docs/spec.md), [возможности ролей](docs/role-capabilities.md)
- [Правила времени](docs/time-rules.md), [JSON-поля](docs/json-fields.md)
- [Frontend](docs/frontend-rules.md), [паттерны UI](frontend/правила%20и%20паттерны%20frontend/паттерны%20UI.md)

Единственная политика внешнего доступа — `config/access.toml`.
У пользователя одна роль; неописанное действие запрещено.
