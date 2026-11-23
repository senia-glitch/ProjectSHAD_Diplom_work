# Тесты статистики репетитора: агрегация линий и сценарий.
# Правила: факт — FINISHED, прогноз — SCHEDULED/ONGOING,
# отмены — 0 ₽, цена — снапшот дня урока, группа считается
# одним уроком репетитора с суммой по линиям.
# Запуск: pytest tests/test_tutor_statistics.py -q
import asyncio
import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ValidationError
from core.utils.security import create_access_token
from app.utils.statistics import (
    aggregate, capacity_stats, duration_hours, line_amount,
    resolve_granularity, time_range_hours,
)
from app.scenarios.tutor.statistics import (
    TutorGetStatisticsDTO,
    TutorGetStatisticsScenario,
)


def dt(y, m, d, h, mi=0):
    return datetime.datetime(y, m, d, h, mi)


def line(lid, sid, start, end, status, price, estimated=False, name=None):
    return {
        "lesson_id": lid, "student_id": sid,
        "student_name": name or f"Ученик #{sid}",
        "start": start, "end": end, "status": status,
        "final_per_hour": price, "estimated": estimated,
    }


def y2030():
    return datetime.date(2030, 1, 1), datetime.date(2030, 12, 31)


# --- pure-агрегация ---


def test_duration_and_amount():
    assert duration_hours(dt(2030, 3, 2, 10), dt(2030, 3, 2, 11, 30)) == 1.5
    assert line_amount(1.5, 1800) == 2700


def test_time_range_hours_accepts_time_and_str():
    assert time_range_hours(datetime.time(8, 0), datetime.time(18, 0)) == 10.0
    assert time_range_hours("08:00:00", "10:30:00") == 2.5
    assert time_range_hours(datetime.time(10, 0), datetime.time(9, 0)) == 0.0


def test_capacity_stats():
    cap = capacity_stats(10.0, 365, 1.0)
    assert cap["weekly_open_hours"] == 10.0
    assert cap["estimated_open_hours"] == 521.43
    assert cap["occupancy_pct"] == 0
    assert capacity_stats(0.0, 365, 5.0)["occupancy_pct"] is None


def test_group_counts_once_but_sums_lines():
    d_from, d_to = y2030()
    lines = [
        line(1, 5, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED", 1800),
        line(1, 6, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED", 1200),
    ]
    res = aggregate(lines, d_from, d_to, "month")
    assert res["totals"]["lessons"] == 1
    assert res["totals"]["tutor_hours"] == 1.0
    assert res["totals"]["billed_hours"] == 2.0
    assert res["totals"]["revenue"] == 3000
    assert [r["student_id"] for r in res["by_student"]] == [5, 6]


def test_fact_forecast_cancelled_split():
    d_from, d_to = y2030()
    lines = [
        line(1, 5, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED", 1800),
        line(2, 5, dt(2030, 3, 3, 10), dt(2030, 3, 3, 11), "SCHEDULED", 1800),
        line(3, 5, dt(2030, 3, 4, 10), dt(2030, 3, 4, 11), "CANCELLED", 1800),
        line(4, 5, dt(2030, 3, 5, 10), dt(2030, 3, 5, 11), "NO_SHOW", 1800),
    ]
    res = aggregate(lines, d_from, d_to, "month")
    t = res["totals"]
    assert (t["lessons"], t["revenue"]) == (1, 1800)
    assert (t["forecast_lessons"], t["forecast_revenue"]) == (1, 1800)
    assert (t["cancelled_lessons"], t["no_show_lessons"]) == (1, 1)


def test_granularity_auto_and_filled_buckets():
    d_from, d_to = y2030()
    res = aggregate([], d_from, d_to, None)
    assert res["granularity"] == "month"
    assert len(res["series"]) == 12
    assert resolve_granularity(d_from, d_from + datetime.timedelta(days=10), None) == "day"
    assert resolve_granularity(d_from, d_from + datetime.timedelta(days=60), None) == "week"


def test_estimated_flag_counted():
    d_from, d_to = y2030()
    lines = [line(1, 5, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED", 1800, True)]
    res = aggregate(lines, d_from, d_to, "month")
    assert res["totals"]["estimated_lines"] == 1
    assert res["by_student"][0]["estimated"] == 1


def test_no_show_per_student():
    d_from, d_to = y2030()
    lines = [
        line(1, 5, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "NO_SHOW", 1800),
        line(2, 6, dt(2030, 3, 3, 10), dt(2030, 3, 3, 11), "FINISHED", 1200),
    ]
    res = aggregate(lines, d_from, d_to, "month")
    assert res["totals"]["no_show_lessons"] == 1
    assert res["totals"]["revenue"] == 1200
    by_id = {r["student_id"]: r for r in res["by_student"]}
    assert by_id[5]["no_show"] == 1
    assert by_id[6]["no_show"] == 0


def test_lost_revenue_and_forecast_hours():
    d_from, d_to = y2030()
    lines = [
        line(1, 5, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "CANCELLED", 1800),
        line(2, 5, dt(2030, 3, 3, 10), dt(2030, 3, 3, 12), "SCHEDULED", 1800),
    ]
    res = aggregate(lines, d_from, d_to, "month")
    assert res["totals"]["lost_revenue"] == 1800
    assert res["totals"]["forecast_hours"] == 2.0
    by_id = {r["student_id"]: r for r in res["by_student"]}
    assert by_id[5]["lost_revenue"] == 1800
    assert by_id[5]["forecast_hours"] == 2.0


# --- сценарий на stub-БД ---


class DummyMetrics:
    async def record(self, *args, **kwargs):
        return None


class StubDB:
    def __init__(self):
        self.tutors = {7: 42}
        self.users = {11: "Иван", 12: "Пётр"}
        self.students = {11: 5, 12: 6}
        self.configs = [{
            "id": 77, "student_id": 5, "tutor_id": 42,
            "hourly_rate": 2000, "discount": 10,
        }, {
            "id": 78, "student_id": 6, "tutor_id": 42,
            "hourly_rate": 1500, "discount": 0,
        }]
        self.lessons = {}
        self.participants = []
        self.bookings = []
        self.statuses = {5: "ACTIVE", 6: "INACTIVE"}

    def seed_lesson(self, lid, start, end, status="SCHEDULED"):
        self.lessons[lid] = {
            "id": lid, "tutor_id": 42,
            "start_time": start, "end_time": end, "status": status,
        }

    def seed_participant(self, lid, sid, snapshot=None):
        self.participants.append({
            "lesson_id": lid, "student_id": sid,
            "participant_settings": {"price_snapshot": snapshot} if snapshot else None,
        })

    async def query(self, sql, params):
        if '"bookings"' in sql:
            return [dict(b) for b in self.bookings if b["tutor_id"] == params["tid"]]
        if '"lesson_participants"' in sql:
            if "GROUP BY" in sql:
                # История: первая/последняя встреча ученика за всё время.
                bounds = {}
                for p in self.participants:
                    lesson = self.lessons[p["lesson_id"]]
                    if lesson["tutor_id"] != params["tid"]:
                        continue
                    cur = bounds.get(p["student_id"])
                    st = lesson["start_time"]
                    if cur is None:
                        bounds[p["student_id"]] = [st, st]
                    else:
                        cur[0] = min(cur[0], st)
                        cur[1] = max(cur[1], st)
                return [
                    {"student_id": sid, "first_start": b[0], "last_start": b[1]}
                    for sid, b in bounds.items()
                ]
            if "lp.participant_settings" in sql and "lp.lesson_id" not in sql.split("FROM")[0]:
                # Новая история: строки без агрегации, фильтр отмен — в сценарии.
                rows = []
                for p in self.participants:
                    lesson = self.lessons[p["lesson_id"]]
                    if lesson["tutor_id"] != params["tid"]:
                        continue
                    rows.append({
                        "student_id": p["student_id"],
                        "start_time": lesson["start_time"],
                        "participant_settings": p["participant_settings"],
                    })
                return rows
            rows = []
            for p in self.participants:
                lesson = self.lessons[p["lesson_id"]]
                if lesson["tutor_id"] != params["tid"]:
                    continue
                if not (params["from"] <= lesson["start_time"] < params["to"]):
                    continue
                if "s1" in params and lesson["status"] not in (params["s1"], params["s2"]):
                    continue
                uid = next(u for u, s in self.students.items() if s == p["student_id"])
                rows.append({
                    "lesson_id": p["lesson_id"], "student_id": p["student_id"],
                    "participant_settings": p["participant_settings"],
                    "start_time": lesson["start_time"], "end_time": lesson["end_time"],
                    "status": lesson["status"], "is_group": lesson.get("is_group", False),
                    "full_name": self.users[uid],
                })
            return rows
        if '"lessons"' in sql:
            return [
                dict(l) for l in self.lessons.values()
                if l["tutor_id"] == params["tid"]
                and params["from"] <= l["start_time"] < params["to"]
            ]
        if '"tutors"' in sql:
            uid = params.get("uid")
            return [{"id": self.tutors[uid]}] if uid in self.tutors else []
        if '"student_settings"' in sql:
            linked = {c["student_id"] for c in self.configs if c["tutor_id"] == params["tid"]}
            return [
                {"student_id": sid, "status": st}
                for sid, st in self.statuses.items() if sid in linked
            ]
        if '"configurations"' in sql:
            return [c for c in self.configs if c["tutor_id"] == params["tid"]]
        return []


def snap(price, cid=77):
    return {
        "hourly_rate": 2000, "discount": 10, "final_per_hour": price,
        "currency": "RUB", "config_id": cid, "snapshot_at": "2030-01-05T09:00:00",
    }


def make_db():
    db = StubDB()
    db.bookings.append({
        "tutor_id": 42, "weekday": "MONDAY",
        "start_time": datetime.time(8, 0), "end_time": datetime.time(18, 0),
    })
    # Групповой завершённый: два ученика, разные цены.
    db.seed_lesson(1, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED")
    db.seed_participant(1, 5, snap(1800))
    db.seed_participant(1, 6, snap(1200))
    # Запланированный без снапшота: цена из живой связи, оценочно.
    db.seed_lesson(2, dt(2030, 4, 2, 10), dt(2030, 4, 2, 11), "SCHEDULED")
    db.seed_participant(2, 5, None)
    # Неявка в мае — для посещаемости и истории.
    db.seed_lesson(3, dt(2030, 5, 6, 10), dt(2030, 5, 6, 11), "NO_SHOW")
    db.seed_participant(3, 5, snap(1800))
    return db


def run(coro):
    return asyncio.run(coro)


def test_scenario_totals_and_students():
    db = make_db()
    sc = TutorGetStatisticsScenario(db=db, metrics=DummyMetrics())
    dto = TutorGetStatisticsDTO(access_token=create_access_token(7, "tutor"), year=2030)
    res = run(sc.execute(dto))
    t = res.totals
    assert (t.lessons, t.revenue) == (1, 3000)
    assert (t.tutor_hours, t.billed_hours) == (1.0, 2.0)
    assert (t.forecast_lessons, t.forecast_revenue) == (1, 1800)
    assert t.forecast_hours == 1.0
    assert t.estimated_lines == 1
    assert res.meta.granularity == "month"
    assert len(res.series) == 12
    march = next(r for r in res.series if r.bucket == "2030-03")
    april = next(r for r in res.series if r.bucket == "2030-04")
    assert (march.lessons, march.revenue, march.tutor_hours) == (1, 3000, 1.0)
    assert (april.forecast_lessons, april.forecast_revenue, april.forecast_hours) == (1, 1800, 1.0)
    by_id = {r.student_id: r for r in res.by_student}
    assert by_id[5].revenue == 1800
    assert by_id[5].forecast_revenue == 1800
    assert by_id[5].forecast_lessons == 1
    assert by_id[6].forecast_lessons == 0
    assert by_id[6].revenue == 1200
    assert by_id[5].student_name == "Иван"
    assert by_id[5].no_show == 1
    assert by_id[6].no_show == 0
    assert by_id[5].first_lesson == "2030-03-02"
    assert by_id[5].last_lesson == "2030-05-06"
    assert by_id[5].status == "ACTIVE"
    assert by_id[6].status == "INACTIVE"
    assert t.no_show_lessons == 1
    april_fore = [c for c in res.by_student_series
                  if c.student_id == 5 and c.bucket == "2030-04"]
    assert [(c.revenue, c.forecast) for c in april_fore] == [(0, 1800)]
    assert [(c.forecast_hours, c.tutor_hours) for c in april_fore] == [(1.0, 0.0)]
    march_fact = [c for c in res.by_student_series
                  if c.student_id == 5 and c.bucket == "2030-03"]
    assert [(c.revenue, c.lessons) for c in march_fact] == [(1800, 1)]
    assert t.lost_revenue == 1800
    assert by_id[5].lost_revenue == 1800
    assert by_id[5].forecast_hours == 1.0
    saturday = next(r for r in res.by_weekday if r.weekday == 5)
    assert (saturday.lessons, saturday.revenue) == (1, 3000)
    assert sum(r.lessons for r in res.by_weekday) == t.lessons
    assert res.capacity.weekly_open_hours == 10.0
    assert res.capacity.estimated_open_hours == 521.43
    assert res.capacity.occupancy_pct == 0
    cell = next(c for c in res.by_weekday if c.weekday == dt(2030, 3, 2, 10).weekday())
    assert (cell.lessons, cell.revenue) == (1, 3000)


def test_scenario_student_filter():
    db = make_db()
    sc = TutorGetStatisticsScenario(db=db, metrics=DummyMetrics())
    dto = TutorGetStatisticsDTO(
        access_token=create_access_token(7, "tutor"), year=2030, student_ids="6",
    )
    res = run(sc.execute(dto))
    assert res.totals.revenue == 1200
    assert [r.student_id for r in res.by_student] == [6]
    assert res.meta.student_ids == [6]


def test_scenario_date_range():
    db = make_db()
    sc = TutorGetStatisticsScenario(db=db, metrics=DummyMetrics())
    dto = TutorGetStatisticsDTO(
        access_token=create_access_token(7, "tutor"), year=2030,
        date_from="2030-03-01", date_to="2030-03-31",
    )
    res = run(sc.execute(dto))
    assert res.totals.lessons == 1
    assert res.totals.forecast_lessons == 0
    assert res.meta.granularity == "day"


def test_scenario_bad_input():
    db = make_db()
    sc = TutorGetStatisticsScenario(db=db, metrics=DummyMetrics())
    with pytest.raises(ValidationError):
        run(sc.execute(TutorGetStatisticsDTO(
            access_token=create_access_token(7, "tutor"), year=2030,
            date_from="2029-12-31", date_to="2030-01-05")))
    with pytest.raises(ValidationError):
        run(sc.execute(TutorGetStatisticsDTO(
            access_token=create_access_token(7, "tutor"), year=2030,
            granularity="fortnight")))


def test_detail_matrices():
    d_from, d_to = y2030()
    lines = [
        line(1, 5, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED", 1800),
        line(1, 6, dt(2030, 3, 2, 10), dt(2030, 3, 2, 11), "FINISHED", 1200),
    ]
    res = aggregate(lines, d_from, d_to, "month")
    wd = dt(2030, 3, 2, 10).weekday()
    assert res["by_hour"] == [{"weekday": wd, "hour": 10, "lessons": 2, "revenue": 3000}]
    assert {"student_id": 5, "weekday": wd, "lessons": 1, "revenue": 1800} in res["by_student_weekday"]
    assert {"student_id": 5, "bucket": "2030-03", "revenue": 1800} in res["by_student_month"]
    assert {"student_id": 6, "bucket": "2030-03", "revenue": 1200} in res["by_student_month"]
    assert {"student_id": 5, "bucket": "2030-03", "revenue": 1800, "forecast": 0,
            "lessons": 1, "forecast_lessons": 0,
            "tutor_hours": 1.0, "forecast_hours": 0.0} in res["by_student_series"]


def test_scenario_upcoming():
    db = make_db()
    start = (datetime.datetime.now() + datetime.timedelta(days=3)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(hours=1)
    db.seed_lesson(10, start, end, "SCHEDULED")
    db.seed_participant(10, 5, snap(1800))
    sc = TutorGetStatisticsScenario(db=db, metrics=DummyMetrics())
    dto = TutorGetStatisticsDTO(
        access_token=create_access_token(7, "tutor"), year=start.year)
    res = run(sc.execute(dto))
    assert len(res.upcoming) == 1
    row = res.upcoming[0]
    assert row.date == start.date().isoformat()
    assert (row.start, row.end, row.minutes) == ("10:00", "11:00", 60)
    assert row.total == 1800
    assert row.students[0].student_id == 5
    assert row.students[0].estimated is False
