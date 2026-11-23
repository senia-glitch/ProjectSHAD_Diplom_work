# OpenFullStackTest

Fullstack-проект: FastAPI-бэкенд и Vue 3/Vite/Pinia-фронтенд.

## Документация

- [SPEC.md](docs/spec.md) — спецификация предметной области
- [ROLE_CAPABILITIES.md](docs/role-capabilities.md) — возможности ролей
- [Актуальные правила фронтенда](docs/frontend-rules.md) — архитектура фронтенда
- [Паттерны UI](frontend/правила%20и%20паттерны%20frontend/паттерны%20UI.md) — дизайн-система
- [Установка стека из 3 пакетов](docs/setup-3-packages.md) — как поднять проект
- [Документация пакетов](docs/) — `fastbase`, `core-package`, `event-infra`

## Запуск

### Бэкенд

```bash
python -m app.main
```

### Фронтенд

```bash
cd frontend
npm install
npm run dev
```

## Вспомогательные скрипты

- `scripts/debug/` — локальные отладочные сценарии (в .gitignore)
- `scripts/smoke/` — ручные smoke-проверки API (`smoke_all.py`, `verify_grid.py`)

## Тесты

```bash
pytest
```
