# Тесты единого JSON-кодека. Запуск: pytest tests/test_json_codec.py -q
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.json_codec import (
    dumps_value,
    parse_value,
    parse_int_list,
    parse_row,
    serialize_for_db,
)


def test_dumps_list_to_str():
    out = dumps_value([1, 2])
    assert isinstance(out, str)
    assert out == "[1, 2]"


def test_dumps_none_and_str_passthrough():
    assert dumps_value(None) is None
    assert dumps_value("already") == "already"


def test_serialize_for_db_tutor_settings():
    # Главный репро 500: [] должен уйти в БД строкой, а не list.
    out = serialize_for_db("tutor_settings", {"hourly_rate": 400.0, "default_links": []})
    assert out["default_links"] == "[]"
    assert out["hourly_rate"] == 400.0


def test_serialize_for_db_keeps_none():
    out = serialize_for_db("bookings", {"access_targets": None})
    assert out["access_targets"] is None


def test_parse_str_list():
    assert parse_value("[1, 2]", "list") == [1, 2]


def test_parse_already_list():
    assert parse_value([1, 2], "list") == [1, 2]


def test_parse_none():
    assert parse_value(None, "list") is None


def test_parse_broken_json_returns_default():
    assert parse_value("not-json{{{", "list") == []
    assert parse_value("not-json{{{", "dict") == {}
    assert parse_value("not-json{{{", "any") is None


def test_parse_int_list_from_str():
    # Баг подстроки: whitelist как str "[12]" не должен матчить student 1.
    wl = parse_int_list("[12]")
    assert wl == [12]
    assert 1 not in wl
    assert 12 in wl


def test_parse_int_list_filters_garbage():
    assert parse_int_list(["1", "x", None, 2.0]) == [1, 2]
    assert parse_int_list(None) == []
    assert parse_int_list("garbage") == []


def test_parse_row_tutor_settings():
    row = {"id": 1, "self_booking_whitelist": "[1,2]", "default_links": [{"a": "b"}]}
    out = parse_row("tutor_settings", row)
    assert out["self_booking_whitelist"] == [1, 2]
    assert out["default_links"] == [{"a": "b"}]
    # исходный dict не мутируется
    assert row["self_booking_whitelist"] == "[1,2]"


def test_old_serialize_compat():
    from app.utils import serialize_json_fields

    out = serialize_json_fields({"default_links": []}, "default_links")
    assert out["default_links"] == "[]"
