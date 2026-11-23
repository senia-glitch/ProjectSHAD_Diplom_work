# Тесты статусов уроков. Запуск: pytest tests/test_lesson_status.py -q
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.lessons import resolve_lesson_status


def dt(h, m=0):
    return datetime.datetime(2026, 10, 12, h, m)


def test_scheduled_before_start():
    assert resolve_lesson_status("SCHEDULED", dt(10), dt(11), dt(9)) == "SCHEDULED"


def test_ongoing_between_start_end():
    assert resolve_lesson_status("SCHEDULED", dt(10), dt(11), dt(10, 30)) == "ONGOING"
    assert resolve_lesson_status("ONGOING", dt(10), dt(11), dt(10, 30)) == "ONGOING"


def test_finished_at_and_after_end():
    assert resolve_lesson_status("ONGOING", dt(10), dt(11), dt(11)) == "FINISHED"
    assert resolve_lesson_status("SCHEDULED", dt(10), dt(11), dt(12)) == "FINISHED"


def test_terminal_never_changes():
    for s in ("FINISHED", "CANCELLED", "NO_SHOW"):
        assert resolve_lesson_status(s, dt(10), dt(11), dt(9)) is None
        assert resolve_lesson_status(s, dt(10), dt(11), dt(10, 30)) is None
        assert resolve_lesson_status(s, dt(10), dt(11), dt(12)) is None


def test_empty_current_treated_as_scheduled():
    assert resolve_lesson_status(None, dt(10), dt(11), dt(12)) == "FINISHED"
    assert resolve_lesson_status("", dt(10), dt(11), dt(9)) == "SCHEDULED"
