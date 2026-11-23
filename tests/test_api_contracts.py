import json
from pathlib import Path

from fastapi.routing import iter_route_contexts
from fastbase import make_app
from core.scenario_registry import ScenarioRegistry


def test_original_api_surface_and_scenario_contracts_are_preserved():
    expected = json.loads((Path(__file__).parent / "fixtures/api_surface.json").read_text(encoding="utf-8"))
    app = make_app()
    routes = {(method, route.path): route for route in iter_route_contexts(app.routes)
              for method in route.methods or ()}
    for item in expected:
        route = routes[(item["method"], item["path"])]
        assert route.endpoint.external_action == item["action"]
        assert route.response_model.__name__ == item["response"]
        if item["scenario"]:
            entry = ScenarioRegistry.get_entry(item["scenario"])
            assert entry.response == route.response_model
    api_routes = {(m, p) for m, p in routes if p.startswith("/api/v1/")}
    assert api_routes == {(i["method"], i["path"]) for i in expected} | {("GET", "/api/v1/ready")}
