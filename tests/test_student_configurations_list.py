# Список репетиторов ученика содержит имя репетитора для карточки списка.
# Запуск: pytest tests/test_student_configurations_list.py -q
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.utils.security import create_access_token
from app.scenarios.student.configurations import (
    StudentGetMyConfigurationsDTO,
    StudentGetMyConfigurationsScenario,
)


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self, rows):
        self.rows = rows
        self.sql = []

    async def query(self, sql, params):
        self.sql.append(sql)
        if '"students"' in sql:
            return [{"id": 5}]
        if '"configurations"' in sql:
            return [dict(r) for r in self.rows]
        return []


def config_row(**extra):
    return {
        "id": 1, "student_id": 5, "tutor_id": 42, "hourly_rate": 1500.0,
        "allow_self_booking": True, "link_visibility_enabled": False,
        "link_lead_time_minutes": 0, **extra,
    }


def run_list(db):
    dto = StudentGetMyConfigurationsDTO(access_token=create_access_token(11, "student"))
    return asyncio.run(StudentGetMyConfigurationsScenario(db=db, metrics=DummyMetrics()).execute(dto))


def test_list_returns_tutor_name():
    db = StubDB([config_row(tutor_username="qa_tutor", tutor_full_name="Тестов Репетитор")])
    res = run_list(db)
    item = res.configurations[0]
    assert item.tutor_username == "qa_tutor"
    assert item.tutor_full_name == "Тестов Репетитор"
    config_sql = next(s for s in db.sql if '"configurations"' in s)
    assert 'LEFT JOIN "tutors"' in config_sql and 'LEFT JOIN "users"' in config_sql


def test_list_without_tutor_user_keeps_optional_fields_empty():
    res = run_list(StubDB([config_row(tutor_username=None, tutor_full_name=None)]))
    item = res.configurations[0]
    assert item.tutor_username is None and item.tutor_full_name is None
    assert item.hourly_rate == 1500.0
