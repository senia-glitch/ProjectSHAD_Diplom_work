# Структурные тесты гвардов пагинации: query-параметры limit/offset
# валидируются на уровне маршрута (out-of-range → 422, а не 500).
# Запуск: pytest tests/test_route_pagination_guards.py -q
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.params import Query

from app.api.v1.routes import admin, logs, notifications, student, tutor

MODULES = [admin, logs, notifications, student, tutor]
# в logs DTO держит le=500 — на маршруте совпадает
LIMIT_CAPS = {"logs": 500}


def _iter_params(router):
    for route in router.routes:
        for param in getattr(route.dependant, "query_params", []):
            yield route.path, param


def _constraints(field_info):
    ge = le = None
    for item in getattr(field_info, "metadata", []) or []:
        code = getattr(item, "ge", None)
        if code is not None and ge is None:
            ge = code
        le2 = getattr(item, "le", None)
        if le2 is not None and le is None:
            le = le2
    return ge, le


def test_all_pagination_params_have_range_guards():
    checked = 0
    for module in MODULES:
        for path, param in _iter_params(module.router):
            module_name = module.__name__.rsplit(".", 1)[-1]
            ge, le = _constraints(param.field_info)
            if param.name == "limit":
                ge2, le2 = ge, le
                assert ge2 == 1 and le2 == LIMIT_CAPS.get(module_name, 1000), \
                    f"{path}: limit гварды {ge}/{le}"
                checked += 1
            if param.name == "offset":
                assert ge == 0, f"{path}: offset ge"
                checked += 1
    assert checked == 24, f"ожидали 24 гвардейских параметра, проверено {checked}"


def test_notifications_limit_default_is_30():
    for path, param in _iter_params(notifications.router):
        if param.name == "limit":
            assert param.field_info.default == 30
            return
    assert False, "notifications limit не найден"
