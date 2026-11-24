import json
from pathlib import Path

from fastapi.routing import iter_route_contexts
from fastbase import make_app
from core.scenario_registry import ScenarioRegistry

FIXTURES = Path(__file__).parent / "fixtures"


def _check(routes, expected):
    for item in expected:
        route = routes[(item["method"], item["path"])]
        assert route.endpoint.external_action == item["action"]
        name = route.response_model.__name__ if route.response_model else None
        assert name == item["response"]
        if item["scenario"]:
            entry = ScenarioRegistry.get_entry(item["scenario"])
            if route.response_model is not None:
                assert entry.response == route.response_model


def test_original_api_surface_and_scenario_contracts_are_preserved():
    """Исходный API SHAD Tutoring неизменен; модули тестов, досок и блога добавлены отдельным контрактом."""
    original = json.loads((FIXTURES / "api_surface.json").read_text(encoding="utf-8"))
    integration = json.loads((FIXTURES / "integration_api_surface.json").read_text(encoding="utf-8"))
    app = make_app()
    routes = {(method, route.path): route for route in iter_route_contexts(app.routes)
              for method in route.methods or ()}
    _check(routes, original)
    _check(routes, integration)
    api_routes = {(m, p) for m, p in routes if p.startswith("/api/v1/")}
    assert api_routes == ({(i["method"], i["path"]) for i in original}
                          | {(i["method"], i["path"]) for i in integration} | {("GET", "/api/v1/ready")})


def test_board_socket_is_declared_in_policy():
    app = make_app()
    sockets = [r for r in iter_route_contexts(app.routes) if r.path == "/api/v1/boards/{board_id}/ws"]
    assert len(sockets) == 1 and sockets[0].endpoint.external_action == "boards.live"
