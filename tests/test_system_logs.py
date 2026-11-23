# Тесты системного журнала: чтение файла фронтенд-лога, фильтры,
# пагинация, устойчивость к битым строкам.
# Запуск: pytest tests/test_system_logs.py -q
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ValidationError
from app.scenarios.system.logs import SystemGetLogsDTO, SystemGetLogsScenario
from app.utils import frontend_log


def run(coro):
    return asyncio.run(coro)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


def write_log(path: Path, rows: list[dict], broken: str | None = None):
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    if broken is not None:
        lines.append(broken)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def entry(ts, lvl="info", cat="api", msg="GET /x", data=None):
    row = {"ts": ts, "lvl": lvl, "cat": cat, "msg": msg}
    if data is not None:
        row["data"] = data
    return row


@pytest.fixture
def log_file(tmp_path, monkeypatch):
    path = tmp_path / "frontend.log"
    write_log(path, [
        entry("2026-10-10T10:00:00.000Z", "info", "api", "→ GET /api/v1/users/me"),
        entry("2026-10-10T10:00:01.000Z", "error", "api", "← GET /api/v1/users/me → 401",
              {"status": 401}),
        entry("2026-10-11T09:30:00.000Z", "warn", "ui", "click:button", {"text": "Войти"}),
        entry("2026-10-11T09:31:00.000Z", "info", "nav", "/login → /schedule"),
    ], broken='{"ts": "2026-10-11T09:32:00.000Z", "lvl": "inf')
    monkeypatch.setattr(frontend_log, "LOG_FILE", path)
    return path


def dto(**kw):
    base = dict(access_token=None)
    base.update(kw)
    return SystemGetLogsDTO(**base)


def scenario():
    return SystemGetLogsScenario(db=None, metrics=DummyMetrics())


# === util ===

def test_read_log_entries_newest_first_skips_broken(log_file):
    rows = frontend_log.read_log_entries()
    assert len(rows) == 4
    assert rows[0]["ts"].startswith("2026-10-11T09:31")


def test_read_log_entries_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(frontend_log, "LOG_FILE", tmp_path / "nope.log")
    assert frontend_log.read_log_entries() == []


# === сценарий ===

def test_logs_page_default(log_file):
    res = run(scenario().execute(dto(limit=2)))
    assert res.total == 4
    assert [i.ts for i in res.items][0].startswith("2026-10-11T09:31")
    assert res.items[0].cat == "nav"


def test_logs_filter_by_level(log_file):
    res = run(scenario().execute(dto(lvl="error")))
    assert res.total == 1
    assert res.items[0].lvl == "error"
    assert res.items[0].data == {"status": 401}


def test_logs_filter_by_category(log_file):
    res = run(scenario().execute(dto(cat="api")))
    assert res.total == 2
    assert all(i.cat == "api" for i in res.items)


def test_logs_filter_by_date(log_file):
    res = run(scenario().execute(dto(date="2026-10-10")))
    assert res.total == 2
    assert all(i.ts.startswith("2026-10-10") for i in res.items)


def test_logs_filter_by_query(log_file):
    res = run(scenario().execute(dto(q="401")))
    assert res.total == 1
    assert "401" in res.items[0].msg


def test_logs_pagination(log_file):
    first = run(scenario().execute(dto(limit=2, offset=0)))
    second = run(scenario().execute(dto(limit=2, offset=2)))
    assert first.total == 4
    assert not {i.ts for i in first.items} & {i.ts for i in second.items}
    assert run(scenario().execute(dto(limit=2, offset=10))).items == []


def test_logs_invalid_date_rejected(log_file):
    with pytest.raises(ValidationError):
        run(scenario().execute(dto(date="10.10.2026")))
