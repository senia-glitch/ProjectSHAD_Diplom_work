"""Real HTTP authorization, without starting the database lifecycle."""
import re

import pytest
from fastapi import FastAPI
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient
from fastbase import make_app
from fastbase.settings import BaseAppSettings
from core.utils.security import create_access_token, create_refresh_token

from app.api.access import install_access, load_policy


@pytest.fixture
def http_app():
    app = make_app()
    install_access(app, BaseAppSettings())
    return app


@pytest.fixture
def client(http_app):
    # No lifespan: denied requests must not call core or touch a database.
    return TestClient(http_app)


def headers(role):
    return {"Authorization": "Bearer " + create_access_token(123, role)}


@pytest.mark.parametrize("role", ["guest", "student", "tutor", "admin", "system"])
def test_every_forbidden_http_action_is_blocked_before_core(http_app, client, role):
    policy = http_app.state.access_policy
    checked = 0
    for route in iter_route_contexts(http_app.routes):
        action = getattr(route.endpoint, "external_action", None)
        if action in policy[role]:
            continue
        path = re.sub(r"\{[^}]+\}", "999999", route.path)
        for method in route.methods or ():
            response = client.request(method, path, headers={} if role == "guest" else headers(role))
            assert response.status_code == (401 if role == "guest" else 403), (role, method, path, response.text)
            assert response.json()["success"] is False
            assert response.headers.get("X-Request-ID")
            checked += 1
    assert checked > 0


@pytest.mark.parametrize("token", [
    "broken", create_refresh_token(123), create_access_token(123, "unknown"),
    create_access_token(123, ["student", "admin"]), create_access_token(0, "admin"),
    create_access_token(123, "guest"),
])
def test_invalid_credentials_do_not_become_guest(client, token):
    response = client.get("/api/v1/health", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401


def test_public_technical_routes_and_wrong_methods(client):
    for path in ("/api/v1/health", "/docs", "/openapi.json", "/redoc"):
        assert client.get(path).status_code == 200
    assert client.post("/api/v1/health").status_code == 405
    assert client.get("/api/v1/unknown").status_code == 404


def test_new_unconfigured_route_is_closed(http_app, client):
    @http_app.get("/unconfigured")
    async def unconfigured():
        raise AssertionError("Unconfigured endpoint must not execute")

    assert client.get("/unconfigured").status_code == 401
    assert client.get("/unconfigured", headers=headers("admin")).status_code == 403


def test_missing_permission_closes_existing_route_and_docs(http_app, client):
    for role in http_app.state.access_policy:
        http_app.state.access_policy[role] = frozenset()
    assert client.get("/docs").status_code == 401
    assert client.get("/openapi.json", headers=headers("admin")).status_code == 403
    assert client.get("/api/v1/health", headers=headers("system")).status_code == 403


@pytest.mark.parametrize("text", [
    "", "[roles.admin]\nscenarios=[]", "[roles.guest]\nscenarios='*'",
    "[roles.guest]\nscenarios=['*']", "[roles.guest]\nscenarios=['a','a']",
])
def test_malformed_policy_fails_closed(tmp_path, text):
    path = tmp_path / "access.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_policy(path)


def test_client_cannot_override_subject_in_body(http_app, client, monkeypatch):
    from app.api.v1.routes import users
    from app.scenarios.users.update_me import UpdateMeResponse

    async def run(name, dto):
        assert name == "update_me"
        assert dto.access_token == trusted_token
        return UpdateMeResponse(user_id=123, username="tester", full_name="Updated",
                                email="test@example.test", personal_number="IND-TEST0001",
                                gender=None, additional_info=None)

    trusted_token = create_access_token(123, "student")
    monkeypatch.setattr(users, "run", run)
    response = client.patch("/api/v1/users/me", headers={"Authorization": "Bearer " + trusted_token},
                            json={"full_name": "Updated", "access_token": create_access_token(1, "admin"),
                                  "user_id": 1, "role": "admin"})
    assert response.status_code == 200
    assert response.json()["user_id"] == 123
