"""Чистая агрегация статистики репетитора. Без IO-зависимостей.

Зерно расчёта — линия (урок × ученик): у каждого ученика даже внутри
одного группового урока своя цена (снапшот дня урока).
Урок в счётчиках — уникальный (группа из трёх считается одним уроком
репетитора), выручка и часы суммируются по линиям.
"""

import datetime
import math

# Факт — урок состоялся, деньги заработаны.
FACT_STATUSES = frozenset({"FINISHED"})
# Прогноз — урок запланирован или идёт прямо сейчас.
FORECAST_STATUSES = frozenset({"SCHEDULED", "ONGOING"})
# Отмены и неявки: 0 ₽, только счётчики.
CANCELLED_STATUSES = frozenset({"CANCELLED", "NO_SHOW"})

GRANULARITIES = ("day", "week", "month")


def duration_hours(
    start_time: datetime.datetime, end_time: datetime.datetime
) -> float:
    """Длительность урока в часах, округлённо до сотых."""
    return round((end_time - start_time).total_seconds() / 3600, 2)


def round_half_up(value: float) -> int:
    """Округление половинных вверх для неотрицательных — зеркало Math.round фронтенда."""
    return int(math.floor(value + 0.5))


def amount_for_line(
    start_time: datetime.datetime, end_time: datetime.datetime, final_per_hour: int | float
) -> int:
    """Выручка линии: точная длительность × замороженная цена часа, одно округление."""
    seconds = (end_time - start_time).total_seconds()
    return round_half_up(final_per_hour * seconds / 3600)


def line_amount(duration_h: float, final_per_hour: int | float) -> int:
    """Выручка линии по уже вычисленной длительности (в часах)."""
    return round_half_up(duration_h * final_per_hour)


def time_range_hours(start_time, end_time) -> float:
    """Длительность интервала в часах. Принимает time/datetime/ISO-строку:
    время броней в БД лежит без даты."""
    day = datetime.date(2000, 1, 1)

    def as_time(value) -> datetime.time:
        if isinstance(value, datetime.datetime):
            return value.time()
        if isinstance(value, datetime.time):
            return value
        return datetime.time.fromisoformat(str(value))

    start = datetime.datetime.combine(day, as_time(start_time))
    end = datetime.datetime.combine(day, as_time(end_time))
    return max(0.0, (end - start).total_seconds() / 3600)


def capacity_stats(
    weekly_open_hours: float, span_days: int, tutor_hours: float
) -> dict:
    """Оценка занятости: открытые часы за период и % загрузки.

    Брони — недельные правила, поэтому открытые часы за произвольный
    диапазон — оценка (недельная норма × недель в диапазоне).
    """
    estimated_open = round(weekly_open_hours * span_days / 7, 2)
    occupancy = (
        round(tutor_hours / estimated_open * 100)
        if estimated_open > 0 else None
    )
    return {
        "weekly_open_hours": round(weekly_open_hours, 2),
        "estimated_open_hours": estimated_open,
        "occupancy_pct": occupancy,
    }


def resolve_granularity(
    date_from: datetime.date, date_to: datetime.date, granularity: str | None
) -> str:
    """Авто-шаг ряда: день до месяца, недели до ~4 месяцев, дальше месяцы."""
    if granularity in GRANULARITIES:
        return granularity
    span = (date_to - date_from).days
    if span <= 31:
        return "day"
    if span <= 124:
        return "week"
    return "month"


def bucket_start(moment: datetime.date, granularity: str) -> datetime.date:
    if granularity == "day":
        return moment
    if granularity == "week":
        return moment - datetime.timedelta(days=moment.weekday())
    return moment.replace(day=1)


def bucket_key(moment: datetime.date, granularity: str) -> str:
    start = bucket_start(moment, granularity)
    if granularity == "day":
        return start.isoformat()
    if granularity == "week":
        iso_year, iso_week, _ = start.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    return start.strftime("%Y-%m")


def iter_buckets(
    date_from: datetime.date, date_to: datetime.date, granularity: str
) -> list[tuple[str, str]]:
    """Все корзины диапазона (ключ, дата начала) — пустые тоже, для графика."""
    out = []
    current = bucket_start(date_from, granularity)
    end = bucket_start(date_to, granularity)
    while current <= end:
        out.append((bucket_key(current, granularity), current.isoformat()))
        if granularity == "day":
            current += datetime.timedelta(days=1)
        elif granularity == "week":
            current += datetime.timedelta(weeks=1)
        else:
            year, month = current.year, current.month + 1
            if month > 12:
                year, month = year + 1, 1
            current = datetime.date(year, month, 1)
    return out


def _empty_totals() -> dict:
    return {
        "lessons": 0,
        "tutor_hours": 0.0,
        "billed_hours": 0.0,
        "revenue": 0,
        "forecast_lessons": 0,
        "forecast_revenue": 0,
        "forecast_hours": 0.0,
        "cancelled_lessons": 0,
        "no_show_lessons": 0,
        "lost_revenue": 0,
        "estimated_lines": 0,
    }


def aggregate(
    lines: list[dict],
    date_from: datetime.date,
    date_to: datetime.date,
    granularity: str | None = None,
) -> dict:
    """Сворачивает линии (урок × ученик) в итоги, ряд и разрез по ученикам.

    Линия: lesson_id, student_id, student_name, start/end (datetime),
    status (эффективный), final_per_hour (int|None — нет цены),
    estimated (bool — цена не из снапшота).
    Уроки без участников в линиях отсутствуют и в счёт не идут.
    """
    step = resolve_granularity(date_from, date_to, granularity)
    totals = _empty_totals()
    lessons: dict[int, dict] = {}
    lesson_revenue: dict[int, int] = {}
    lesson_forecast: dict[int, int] = {}
    students: dict[int, dict] = {}
    series: dict[str, dict] = {
        key: {"bucket": key, "bucket_start": start, "lessons": 0,
              "revenue": 0, "tutor_hours": 0.0,
              "forecast_lessons": 0, "forecast_revenue": 0, "forecast_hours": 0.0}
        for key, start in iter_buckets(date_from, date_to, step)
    }

    for line in lines:
        lid = line["lesson_id"]
        info = lessons.get(lid)
        if info is None:
            dur = duration_hours(line["start"], line["end"])
            info = {
                "bucket": bucket_key(line["start"].date(), step),
                "weekday": line["start"].date().weekday(),
                "duration": dur,
                "status": line["status"],
            }
            lessons[lid] = info
        status = info["status"]
        if line.get("estimated"):
            totals["estimated_lines"] += 1

        student = students.get(line["student_id"])
        if student is None:
            student = {
                "student_id": line["student_id"],
                "student_name": line.get("student_name") or f"Ученик #{line['student_id']}",
                "lessons": set(),
                "billed_hours": 0.0,
                "revenue": 0,
                "forecast_revenue": 0,
                "forecast_hours": 0.0,
                "cancelled": 0,
                "estimated": 0,
                "no_show": 0,
                "lost_revenue": 0,
                "forecast_lessons": set(),
            }
            students[line["student_id"]] = student

        if status in FACT_STATUSES:
            amount = amount_for_line(line["start"], line["end"], line["final_per_hour"] or 0)
            totals["revenue"] += amount
            totals["billed_hours"] = round(totals["billed_hours"] + info["duration"], 2)
            lesson_revenue[lid] = lesson_revenue.get(lid, 0) + amount
            student["revenue"] += amount
            student["billed_hours"] = round(student["billed_hours"] + info["duration"], 2)
            student["lessons"].add(lid)
        elif status in FORECAST_STATUSES:
            amount = amount_for_line(line["start"], line["end"], line["final_per_hour"] or 0)
            totals["forecast_revenue"] += amount
            lesson_forecast[lid] = lesson_forecast.get(lid, 0) + amount
            student["forecast_revenue"] += amount
            student["forecast_lessons"].add(lid)
            student["forecast_hours"] = round(student["forecast_hours"] + info["duration"], 2)
        elif status == "CANCELLED":
            totals.setdefault("_cancelled_ids", set()).add(lid)
            student["cancelled"] += 1
            missed = amount_for_line(line["start"], line["end"], line["final_per_hour"] or 0)
            totals["lost_revenue"] += missed
            student["lost_revenue"] += missed
        elif status == "NO_SHOW":
            totals.setdefault("_no_show_ids", set()).add(lid)
            student["no_show"] += 1
            missed = amount_for_line(line["start"], line["end"], line["final_per_hour"] or 0)
            totals["lost_revenue"] += missed
            student["lost_revenue"] += missed
        if line.get("estimated"):
            student["estimated"] += 1

    for lid, info in lessons.items():
        bucket = series.get(info["bucket"])
        if bucket is None:
            continue
        if info["status"] in FACT_STATUSES:
            bucket["lessons"] += 1
            bucket["revenue"] += lesson_revenue.get(lid, 0)
            bucket["tutor_hours"] = round(bucket["tutor_hours"] + info["duration"], 2)
            totals["lessons"] += 1
            totals["tutor_hours"] = round(totals["tutor_hours"] + info["duration"], 2)
        elif info["status"] in FORECAST_STATUSES:
            totals["forecast_lessons"] += 1
            totals["forecast_hours"] = round(totals["forecast_hours"] + info["duration"], 2)
            bucket["forecast_lessons"] += 1
            bucket["forecast_revenue"] += lesson_forecast.get(lid, 0)
            bucket["forecast_hours"] = round(bucket["forecast_hours"] + info["duration"], 2)

    totals["cancelled_lessons"] = len(totals.pop("_cancelled_ids", set()))
    totals["no_show_lessons"] = len(totals.pop("_no_show_ids", set()))

    by_student = []
    for student in students.values():
        by_student.append({
            "student_id": student["student_id"],
            "student_name": student["student_name"],
            "lessons": len(student["lessons"]),
            "billed_hours": student["billed_hours"],
            "revenue": student["revenue"],
            "forecast_revenue": student["forecast_revenue"],
            "forecast_lessons": len(student["forecast_lessons"]),
            "forecast_hours": student["forecast_hours"],
            "cancelled": student["cancelled"],
            "no_show": student["no_show"],
            "lost_revenue": student["lost_revenue"],
            "estimated": student["estimated"],
        })
    by_student.sort(key=lambda r: (-r["revenue"], r["student_name"]))

    by_weekday = [
        {"weekday": wd, "lessons": 0, "revenue": 0} for wd in range(7)
    ]
    for lid, info in lessons.items():
        if info["status"] in FACT_STATUSES:
            cell = by_weekday[info["weekday"]]
            cell["lessons"] += 1
            cell["revenue"] += lesson_revenue.get(lid, 0)

    # Детализация для heatmap и спарклайнов: только ненулевые ячейки.
    by_hour: dict[tuple[int, int], dict] = {}
    by_student_weekday: dict[tuple[int, int], dict] = {}
    by_student_month: dict[tuple[int, str], dict] = {}
    for line in lines:
        if lessons[line["lesson_id"]]["status"] not in FACT_STATUSES:
            continue
        amount = amount_for_line(
            line["start"], line["end"], line["final_per_hour"] or 0
        )
        hour_key = (line["start"].date().weekday(), line["start"].hour)
        cell = by_hour.get(hour_key)
        if cell is None:
            cell = {"weekday": hour_key[0], "hour": hour_key[1], "lessons": 0, "revenue": 0}
            by_hour[hour_key] = cell
        cell["lessons"] += 1
        cell["revenue"] += amount
        sw_key = (line["student_id"], line["start"].date().weekday())
        sw = by_student_weekday.get(sw_key)
        if sw is None:
            sw = {"student_id": sw_key[0], "weekday": sw_key[1], "lessons": 0, "revenue": 0}
            by_student_weekday[sw_key] = sw
        sw["lessons"] += 1
        sw["revenue"] += amount
        sm_key = (line["student_id"], bucket_key(line["start"].date(), "month"))
        sm = by_student_month.get(sm_key)
        if sm is None:
            sm = {"student_id": sm_key[0], "bucket": sm_key[1], "revenue": 0}
            by_student_month[sm_key] = sm
        sm["revenue"] += amount

    # Ряд ученика в шаге периода: факт и прогноз отдельно.
    # Кормит график одного ученика и спарклайны топа.
    by_student_series: dict[tuple[int, str], dict] = {}
    for line in lines:
        info = lessons[line["lesson_id"]]
        key = (line["student_id"], bucket_key(line["start"].date(), step))
        cell = by_student_series.get(key)
        if cell is None:
            cell = {"student_id": key[0], "bucket": key[1],
                    "revenue": 0, "forecast": 0, "lessons": 0, "forecast_lessons": 0,
                    "tutor_hours": 0.0, "forecast_hours": 0.0}
            by_student_series[key] = cell
        amount = amount_for_line(line["start"], line["end"], line["final_per_hour"] or 0)
        if info["status"] in FACT_STATUSES:
            cell["revenue"] += amount
            cell["lessons"] += 1
            cell["tutor_hours"] = round(cell["tutor_hours"] + info["duration"], 2)
        elif info["status"] in FORECAST_STATUSES:
            cell["forecast"] += amount
            cell["forecast_lessons"] += 1
            cell["forecast_hours"] = round(cell["forecast_hours"] + info["duration"], 2)

    return {
        "totals": totals,
        "series": [series[key] for key, _ in iter_buckets(date_from, date_to, step)],
        "by_student": by_student,
        "by_weekday": by_weekday,
        "by_hour": sorted(by_hour.values(), key=lambda c: (c["weekday"], c["hour"])),
        "by_student_weekday": sorted(by_student_weekday.values(), key=lambda c: (c["student_id"], c["weekday"])),
        "by_student_month": sorted(by_student_month.values(), key=lambda c: (c["student_id"], c["bucket"])),
        "by_student_series": sorted(by_student_series.values(), key=lambda c: (c["student_id"], c["bucket"])),
        "granularity": step,
    }
