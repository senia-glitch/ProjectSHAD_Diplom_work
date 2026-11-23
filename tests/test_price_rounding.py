# Тесты корректности округления цены/сумм (фронтенд-эталон Math.round,
# суммы — одно округление от точной длительности). Запуск: pytest tests/test_price_rounding.py -q
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.participants import final_price_per_hour
from app.utils.statistics import amount_for_line, aggregate, line_amount


def test_final_price_matches_frontend_math_round():
    # Полуцелые кейсы, расходившиеся с frontend pricing.finalPrice раньше.
    assert final_price_per_hour(350, 25) == 263    # 262.5 -> 263 (было 262)
    assert final_price_per_hour(1246, 25) == 935   # 934.5 -> 935 (было 934)
    assert final_price_per_hour(109, 50) == 55     # 54.5 -> 55 (было 54)
    assert final_price_per_hour(501, 50) == 251    # 250.5 -> 251 (было 250)
    # Регресс ранее закреплённых кейсов.
    assert final_price_per_hour(1000, 40) == 600
    assert final_price_per_hour(1000, 0) == 1000
    assert final_price_per_hour(999, 10) == 899


def _line(price: int, status: str = "FINISHED"):
    return {
        "lesson_id": 1,
        "student_id": 1,
        "start": datetime.datetime(2030, 6, 4, 17, 30),
        "end": datetime.datetime(2030, 6, 4, 18, 40),  # 70 минут
        "status": status,
        "final_per_hour": price,
        "estimated": False,
    }


def test_amount_counts_exact_duration_not_premultiplied():
    # 70 мин * 103 €/час: точное 120.166... -> 120 (раньше 121 из-за
    # двойного округления duration_hours до сотых).
    start = datetime.datetime(2030, 6, 4, 17, 30)
    end = datetime.datetime(2030, 6, 4, 18, 40)
    assert amount_for_line(start, end, 103) == 120
    assert amount_for_line(start, end, 121) == 141  # точное 141.166 -> 141 (было 142)


def test_aggregate_uses_exact_duration():
    result = aggregate([_line(103)], datetime.date(2030, 6, 1), datetime.date(2030, 6, 30), "day")
    assert result["totals"]["revenue"] == 120
    assert result["totals"]["lessons"] == 1
    assert result["totals"]["billed_hours"] == 1.17  # отображение длительности не изменилось


def test_aggregate_forecast_and_cancelled():
    forecast = aggregate([_line(103, status="SCHEDULED")], datetime.date(2030, 6, 1), datetime.date(2030, 6, 30), "day")
    assert forecast["totals"]["forecast_revenue"] == 120

    lost = aggregate([_line(103, status="CANCELLED")], datetime.date(2030, 6, 1), datetime.date(2030, 6, 30), "day")
    assert lost["totals"]["lost_revenue"] == 120


def test_line_amount_helper_still_half_up():
    # Обратная совместимость сигнатуры: одно округление, полуцелые вверх.
    assert line_amount(1.0, 103) == 103
    assert line_amount(0.5, 5) == 3  # 2.5 -> 3 (Math.round-семантика)
