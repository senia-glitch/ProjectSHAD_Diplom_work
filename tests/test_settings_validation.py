# Тесты валидаций: display-окно (БАГ 14), year=0 (БАГ 10).
# Запуск: pytest tests/test_settings_validation.py -q
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ValidationError
from core.utils.security import create_access_token

from app.utils.validation import (
    TIME_OF_DAY_PATTERN,
    TIME_OF_DAY_START_PATTERN,
    time_of_day_value,
)
from app.scenarios.student.profile import StudentUpdateMySettingsDTO, StudentUpdateMySettingsScenario
from app.scenarios.tutor.profile import TutorUpdateMySettingsDTO, TutorUpdateMySettingsScenario
from app.scenarios.tutor.statistics import TutorGetStatisticsDTO, TutorGetStatisticsScenario


def run(coro):
    return asyncio.run(coro)


class M:
    async def record(self, *a, **k):
        return None


class SettingsStubDB:
    def __init__(self, table_rows):
        self.table_rows = table_rows  # "tutor_settings"/"student_settings"

    async def query(self, sql, params):
        if '"tutor_settings"' in sql:
            if "SELECT id" in sql:
                return [{"id": s["id"], "display_time_from": s["display_time_from"],
                         "display_time_to": s["display_time_to"]}
                        for s in self.table_rows["tutor_settings"]]
            return [dict(s) for s in self.table_rows["tutor_settings"]]
        if '"student_settings"' in sql:
            return [dict(s) for s in self.table_rows["student_settings"]]
        if '"students"' in sql and "user_id" in sql:
            return [{"id": 5}]
        if '"tutors"' in sql and "user_id" in sql:
            return [{"id": 42}]
        if '"configurations"' in sql:
            return []
        return []

    async def update(self, table, rid, data):
        for row in self.table_rows.get(table, []):
            if row["id"] == rid:
                row.update(data)
                return dict(row)
        return {}

    async def delete(self, table, rid):
        return True


def test_time_of_day_unit_values():
    assert time_of_day_value("00:00").hour == 0
    assert time_of_day_value("24:00") is not None
    assert time_of_day_value("24:00").hour == 23 and time_of_day_value("24:00").minute == 59
    with pytest.raises(ValueError):
        time_of_day_value("25:00")


def test_start_pattern_forbids_24_00_end_pattern_allows():
    assert TIME_OF_DAY_START_PATTERN.startswith("^")
    import re
    assert not re.match(TIME_OF_DAY_START_PATTERN, "24:00")
    assert re.match(TIME_OF_DAY_PATTERN, "24:00")


# ---套餐 14:(student) окно отображения ---

STUDENT_SETTINGS = [{
    "id": 7, "student_id": 5, "status": "ACTIVE", "timezone_offset": 0,
    "schedule_view": "INFORMATIVE", "display_time_from": "08:00", "display_time_to": "23:59",
}]


def test_student_from_24_00_rejected_by_pattern():
    with pytest.raises(Exception):  # pydantic ValidationError from pattern
        StudentUpdateMySettingsDTO(access_token="x", display_time_from="24:00")


def test_student_from_equal_to_rejected():
    stub = SettingsStubDB({"student_settings": STUDENT_SETTINGS})
    sc = StudentUpdateMySettingsScenario(db=stub, metrics=M())
    with pytest.raises(ValidationError):
        run(sc.execute(StudentUpdateMySettingsDTO(
            access_token=create_access_token(11, "student"),
            display_time_from="20:00", display_time_to="08:00",
        )))


def test_student_valid_window_saved():
    stub = SettingsStubDB({"student_settings": STUDENT_SETTINGS})
    sc = StudentUpdateMySettingsScenario(db=stub, metrics=M())
    res = run(sc.execute(StudentUpdateMySettingsDTO(
        access_token=create_access_token(11, "student"),
        display_time_from="07:00", display_time_to="24:00",
    )))
    assert res.display_time_from == "07:00"
    assert res.display_time_to == "24:00"


def test_student_unrelated_fields_do_not_hit_window_check():
    # Легаси-данные с перегнутым окном не блокируют изменение статуса.
    rows = [dict(s) for s in STUDENT_SETTINGS]
    rows[0]["display_time_from"], rows[0]["display_time_to"] = "22:00", "06:00"
    stub = SettingsStubDB({"student_settings": rows})
    sc = StudentUpdateMySettingsScenario(db=stub, metrics=M())
    res = run(sc.execute(StudentUpdateMySettingsDTO(
        access_token=create_access_token(11, "student"), status="INACTIVE",
    )))
    assert res.status == "INACTIVE"


# ---套餐 14:(tutor) окно отображения ---

TUTOR_SETTINGS = [{
    "id": 8, "tutor_id": 42, "hourly_rate": 1500, "discount": 0, "timezone_offset": 0,
    "work_status": "WORKING", "schedule_type": "INFORMATIVE",
    "display_time_from": "08:00", "display_time_to": "23:59",
    "self_booking_mode": "YES", "self_booking_whitelist": None,
    "booking_lead_time_hours": 24, "cancellation_lead_time_hours": 24, "default_links": None,
}]


def test_tutor_from_24_00_rejected_by_pattern():
    with pytest.raises(Exception):
        TutorUpdateMySettingsDTO(access_token="x", display_time_from="24:00")


def test_tutor_inverted_window_rejected():
    stub = SettingsStubDB({"tutor_settings": TUTOR_SETTINGS})
    sc = TutorUpdateMySettingsScenario(db=stub, metrics=M())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorUpdateMySettingsDTO(
            access_token=create_access_token(7, "tutor"),
            display_time_from="23:00", display_time_to="08:00",
        )))


def test_tutor_valid_window_saved():
    stub = SettingsStubDB({"tutor_settings": TUTOR_SETTINGS})
    sc = TutorUpdateMySettingsScenario(db=stub, metrics=M())
    res = run(sc.execute(TutorUpdateMySettingsDTO(
        access_token=create_access_token(7, "tutor"),
        display_time_from="08:30", display_time_to="24:00",
    )))
    assert res.display_time_to == "24:00"


# ---套餐 10: year=0 больше не обходят собственную валидацию ---


class EmptyStatsStubDB:
    async def query(self, sql, params):
        if '"tutors"' in sql:
            return [{"id": 42}]
        return []

    async def create(self, table, data):
        return {}

    async def update(self, table, rid, data):
        return {}

    async def delete(self, table, rid):
        return True


@pytest.mark.parametrize("bad_year", [0, 1999, 2101])
def test_statistics_invalid_years_rejected(bad_year):
    stub = EmptyStatsStubDB()
    sc = TutorGetStatisticsScenario(db=stub, metrics=M())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorGetStatisticsDTO(access_token=create_access_token(7, "tutor"), year=bad_year)))
