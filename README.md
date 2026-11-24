# SHAD Tutoring / OpenFullStackTest

Платформа для репетиторов и учеников: расписание, брони, уроки, учёт оплат,
уведомления и статистика, а также **тесты** с автопроверкой, **совместные доски**
в реальном времени и **личный блог** репетитора. Backend: **event-infra + core-package +
fastbase + PostgreSQL**, один процесс и одна БД. Frontend: Vue 3 / Vite / Pinia.

В проект встроены ProjectSHAD_Diplom_testirovanie (тесты) и ProjectSHAD_Diplom_work_doska
(доски); интерфейс оформлен по эталону My_Blog: тёмный деловой стиль с индиго-акцентом,
светлая тема в шапке, раскладка для телефона. Что и куда перенесено, правила доступа
и устройство модулей — [docs/integration.md](docs/integration.md).

| Раздел | Репетитор | Ученик | Гость |
|---|---|---|---|
| Тесты `/testing` | создаёт тесты, открывает доступ своим ученикам, проверяет и оценивает | проходит доступные тесты, видит результаты | — |
| Доски `/boards` | создаёт доски, приглашает по коду, исключает участников | входит по коду | — |
| Блог `/blog` | ведёт свой блог (`/blog/manage`), отвечает в комментариях | читает и комментирует | читает |

## Запуск в Docker одной командой

Запустить Docker Desktop (Linux containers), затем из папки проекта:

```powershell
.\dev.ps1
```

Скрипт создаст локальные настройки, соберёт frontend и backend, запустит
PostgreSQL, применит миграции и дождётся готовности проекта.
Приложение: [localhost:3000](http://localhost:3000/), API-документация:
[localhost:3000/docs](http://localhost:3000/docs/).
Docker начинает с пустой отдельной БД; данные сохраняются в постоянном томе.

```powershell
.\dev.ps1 down       # остановить с сохранением данных
.\dev.ps1 up         # снова запустить
.\dev.ps1 logs       # посмотреть логи
.\dev.ps1 test       # backend и frontend в контейнерах
.\dev.ps1 help       # все команды
```

Для этого режима локальные Python, Node и PostgreSQL не нужны.
Порты, данные, секреты и устройство контейнеров — в [docs/docker.md](docs/docker.md).

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

Демо-данные (репетитор `demo_tutor`, ученик `demo_student`, пароль `demo12345`, тест, запись
блога и доска) в уже запущенное приложение; для Docker — адрес `http://localhost:3000`:

```powershell
.\venv\Scripts\python.exe -m scripts.seed_demo --api http://127.0.0.1:8000
```

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

- [Объединение проектов: тесты, доски, блог, дизайн](docs/integration.md)
- [Карта адаптации и результаты проверок](docs/stack-adaptation.md)
- [Docker и PowerShell-запуск](docs/docker.md)
- [Архитектура, правила и назначение проекта](PROJECT.md)
- [Спецификация](docs/spec.md), [возможности ролей](docs/role-capabilities.md)
- [Правила времени](docs/time-rules.md), [JSON-поля](docs/json-fields.md)
- [Frontend](docs/frontend-rules.md), [паттерны UI](frontend/правила%20и%20паттерны%20frontend/паттерны%20UI.md)

Единственная политика внешнего доступа — `config/access.toml`.
У пользователя одна роль; неописанное действие запрещено.
