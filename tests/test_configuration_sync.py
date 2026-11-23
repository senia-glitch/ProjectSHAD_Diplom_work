# Тесты синка самозаписи: флаг конфигурации <-> whitelist настроек.
# Запуск: pytest tests/test_configuration_sync.py -q
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.configurations import (
    resolve_allow_self_booking,
    sync_allow_self_booking_into_whitelist,
)


def test_resolve_yes_opens_for_everyone():
    assert resolve_allow_self_booking("YES", [], 5) is True
    assert resolve_allow_self_booking("YES", None, 5) is True


def test_resolve_no_follows_whitelist():
    assert resolve_allow_self_booking("NO", [5], 5) is True
    assert resolve_allow_self_booking("NO", [7], 5) is False
    assert resolve_allow_self_booking("NO", None, 5) is False
    assert resolve_allow_self_booking("NO", "[5]", 5) is True


def test_sync_adds_on_allow():
    assert sync_allow_self_booking_into_whitelist([], 5, True) == [5]
    assert sync_allow_self_booking_into_whitelist([5], 5, True) == [5]


def test_sync_removes_on_deny():
    assert sync_allow_self_booking_into_whitelist([5, 7], 5, False) == [7]
    assert sync_allow_self_booking_into_whitelist([7], 5, False) == [7]
