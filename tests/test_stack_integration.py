"""Opt-in HTTP → core → event-infra → PostgreSQL regression.

Run with SHAD_RUN_DB_TESTS=1. Only the configured, distinct TEST_DB_URL is used.
"""
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import secrets

import pytest

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.getenv("SHAD_RUN_DB_TESTS") != "1", reason="Set SHAD_RUN_DB_TESTS=1")]


def test_preserved_product_actions_on_postgresql(monkeypatch, tmp_path):
    from scripts.db_config import select_database
    from scripts.migrate import migrate
    # Select once, before application/lifespan; never clean the application DB.
    url = select_database(test=True)
    migrate()
    from sqlalchemy import create_engine, text
    from fastapi.testclient import TestClient
    from fastapi.routing import iter_route_contexts
    from core.utils.security import create_access_token
    from app.main import app
    from app.utils import frontend_log

    monkeypatch.setattr(frontend_log, "LOG_FILE", tmp_path / "frontend.log")
    engine = create_engine(url, hide_parameters=True)
    suffix = secrets.token_hex(5)
    password = secrets.token_hex(12)
    created = []
    successful = set()

    with TestClient(app, raise_server_exceptions=False) as client:
        def request(method, path, actor=None, body=None, params=None, status=200):
            headers = {"Authorization": "Bearer " + actor["access_token"]} if actor else {}
            response = client.request(method, "/api/v1" + path, headers=headers, json=body, params=params)
            assert response.status_code == status, (method, path, response.status_code, response.text)
            if status == 200:
                scope = {"type": "http", "path": "/api/v1" + path, "root_path": "", "method": method}
                from starlette.routing import Match
                route = next(r for r in iter_route_contexts(app.routes) if r.matches(scope)[0] == Match.FULL)
                successful.add(route.endpoint.external_action)
            return response.json()

        def register(role, name):
            account = request("POST", "/users/register", body={
                "role": role, "username": f"test_{suffix}_{name}", "password": password,
                "full_name": f"Integration {name}", "email": f"{suffix}_{name}@example.test"})
            created.append(account)
            return account

        try:
            assert request("GET", "/health") == {"status": "ok"}
            assert request("GET", "/ready") == {"status": "ready"}
            assert "offset_hours" in request("GET", "/system/server-time")
            tutor, student, other = register("tutor", "tutor"), register("student", "student"), register("student", "other")
            # An administrator is a fixture, not an open-registration capability.
            with engine.begin() as connection:
                admin_id = connection.execute(text('''INSERT INTO users
                    (role_id, username, personal_number, password_hash, full_name, email, created_at)
                    SELECT id, :username, :number, 'unused-fixture-password', 'Integration admin', :email, :created
                    FROM roles WHERE name='admin' RETURNING id'''),
                    {"username": f"test_{suffix}_admin", "number": f"TEST-{suffix}",
                     "email": f"{suffix}_admin@example.test", "created": datetime.now()}).scalar_one()
                connection.execute(text('INSERT INTO admins (user_id) VALUES (:id)'), {"id": admin_id})
            admin = {"user_id": admin_id, "access_token": create_access_token(admin_id, "admin")}
            created.append(admin)
            for actor, prefix in ((tutor, "tutor"), (student, "student"), (admin, "admin")):
                request("GET", "/users/me", actor)
                request("GET", f"/{prefix}/me", actor)
            tutor_info = request("GET", "/users/me", tutor)
            student_info = request("GET", "/users/me", student)
            request("PATCH", "/users/me", student, {"full_name": "Updated integration student"})
            assert request("GET", "/users/me", student)["full_name"] == "Updated integration student"
            request("PATCH", "/tutor/me/settings", tutor, {"hourly_rate": 2000, "discount": 10,
                    "booking_lead_time_hours": 0, "cancellation_lead_time_hours": 0})
            request("PATCH", "/student/me/settings", student, {"status": "ACTIVE", "timezone_offset": 8})
            assert request("GET", "/tutor/me", tutor)["hourly_rate"] == 2000
            assert request("GET", "/student/me", student)["timezone_offset"] == 8
            tid, sid, oid = tutor["user_id"], student["user_id"], other["user_id"]
            config = request("POST", "/tutor/configurations", tutor, {"student_user_id": sid})
            cid = config["config_id"]
            request("GET", "/tutor/configurations", tutor)
            request("GET", "/student/configurations", student)
            request("GET", f"/tutor/configurations/{cid}", tutor)
            request("GET", f"/student/configurations/{cid}", student)
            request("GET", f"/student/configurations/{cid}", other, status=404)
            request("PATCH", f"/tutor/configurations/{cid}", tutor, {"hourly_rate": 1800, "slot_step_minutes": 30})
            request("POST", f"/tutor/configurations/{cid}/reset", tutor)
            request("DELETE", f"/student/configurations/{cid}", student)
            cid = request("POST", "/student/configurations", student, {"tutor_user_id": tid})["config_id"]
            request("DELETE", f"/tutor/configurations/{cid}", tutor)
            cid = request("POST", "/student/configurations/by-code", student,
                          {"personal_number": tutor_info["personal_number"]})["config_id"]
            request("DELETE", f"/student/configurations/{cid}", student)
            cid = request("POST", "/tutor/configurations/by-code", tutor,
                          {"personal_number": student_info["personal_number"]})["config_id"]
            request("POST", "/tutor/configurations", tutor, {"student_user_id": oid})

            future = (datetime.now() + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
            date_range = {"date_from": future.date().isoformat(), "date_to": future.date().isoformat()}
            weekday = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")[future.weekday()]
            booking = request("POST", "/tutor/bookings", tutor,
                              {"weekday": weekday, "start_time": "08:00", "end_time": "20:00"})
            bid = booking["booking_id"]
            request("GET", "/tutor/me/bookings", tutor)
            request("PATCH", f"/tutor/bookings/{bid}", tutor, {"start_time": "09:00"})
            slots = request("GET", f"/student/tutors/{tid}/slots", student, params=date_range)
            assert slots["slots"]
            lesson_body = {"start_time": future.isoformat(), "end_time": (future + timedelta(hours=1)).isoformat(),
                           "is_group": True, "lesson_links": [{"title": "Meeting", "url": "https://example.test/lesson"}]}
            lesson = request("POST", "/tutor/lessons", tutor, lesson_body)
            lid = lesson["lesson_id"]
            request("POST", "/tutor/lessons", tutor, lesson_body, status=409)
            request("GET", "/tutor/me/lessons", tutor, params=date_range)
            request("GET", f"/tutor/lessons/{lid}", tutor)
            request("PATCH", f"/tutor/lessons/{lid}", tutor, {"lesson_descriptions": "Preserved HTTP/core behavior"})
            request("POST", f"/tutor/lessons/{lid}/participants", tutor, {"student_user_id": sid})
            request("GET", f"/tutor/lessons/{lid}/participants", tutor)
            request("PATCH", f"/tutor/lessons/{lid}/participants/{sid}/payment", tutor, {"paid": True})
            details = request("GET", f"/tutor/lessons/{lid}", tutor)
            assert details["descriptions"] == "Preserved HTTP/core behavior"
            assert details["students"][0]["paid"] is True
            assert details["students"][0]["amount"] == 1800
            request("PATCH", f"/tutor/configurations/{cid}", tutor, {"hourly_rate": 2400})
            assert request("GET", f"/tutor/lessons/{lid}", tutor)["students"][0]["amount"] == 1800
            request("GET", "/student/me/lessons", student, params=date_range)
            request("GET", f"/student/lessons/{lid}", student)
            request("GET", f"/student/tutors/{tid}/lessons", student, params=date_range)
            request("GET", "/tutor/lessons/details", tutor, params=date_range)
            request("GET", f"/tutor/students/{sid}/busy-slots", tutor, params=date_range)
            request("GET", "/tutor/students", tutor)
            request("GET", "/tutor/statistics", tutor, params=date_range)
            request("DELETE", f"/tutor/lessons/{lid}/participants/{sid}", tutor)
            request("POST", f"/student/lessons/{lid}/join", student)
            request("DELETE", f"/student/lessons/{lid}/leave", student)
            request("DELETE", f"/tutor/lessons/{lid}", tutor)
            own = request("POST", "/student/lessons", student, {"tutor_user_id": tid, **lesson_body, "is_group": False})
            request("GET", f"/student/lessons/{own['lesson_id']}", other, status=404)
            request("DELETE", f"/tutor/lessons/{own['lesson_id']}", tutor)
            request("DELETE", f"/tutor/bookings/{bid}", tutor)

            notes = request("GET", "/notifications", student)
            assert notes["notifications"]
            request("GET", "/notifications/unread-count", student)
            request("POST", f"/notifications/{notes['notifications'][0]['id']}/read", student)
            request("POST", "/notifications/read-all", student)
            assert request("GET", "/notifications/unread-count", student)["count"] == 0
            request("POST", "/logs", student, {"logs": [{"ts": datetime.now().isoformat(), "lvl": "info",
                    "cat": "integration", "msg": "stack verified"}]})
            assert request("GET", "/logs", admin, params={"q": "stack verified"})["total"] == 1
            for path in ("/admin/users", "/admin/students", "/admin/tutors", "/admin/admins", "/system/stats"):
                request("GET", path, admin)
            request("POST", "/system/init-roles", admin)
            request("GET", f"/admin/users/{sid}", admin)
            request("PATCH", f"/admin/users/{sid}", admin, {"full_name": "Admin-edited integration student"})
            assert request("GET", "/users/me", student)["full_name"] == "Admin-edited integration student"
            request("POST", "/users/me/change-password", student, {"old_password": password, "new_password": password + "x"})
            login = request("POST", "/auth/login", body={"username": f"test_{suffix}_student", "password": password + "x"})
            refreshed = request("POST", "/auth/refresh", body={"refresh_token": login["refresh_token"]})
            request("POST", "/auth/refresh", body={"refresh_token": login["refresh_token"]}, status=422)
            request("POST", "/auth/logout", body={"refresh_token": refreshed["refresh_token"]})
            request("POST", "/auth/refresh", body={"refresh_token": refreshed["refresh_token"]}, status=422)
            request("POST", "/users/me/delete", other, {})
            expected = json.loads((Path(__file__).parent / "fixtures/api_surface.json").read_text(encoding="utf-8"))
            actions = {row["action"] for row in expected} | {"service.ready"}
            assert actions <= successful, f"Unverified actions: {sorted(actions - successful)}"
            Path(".tmp/integration-actions.json").write_text(json.dumps(sorted(successful), indent=2), encoding="utf-8")
        finally:
            # Remove only this run's accounts through the preserved account lifecycle.
            for account in reversed(created):
                if account.get("role") in ("student", "tutor"):
                    client.post("/api/v1/users/me/delete", headers={"Authorization": "Bearer " + account["access_token"]}, json={})
            with engine.begin() as connection:
                connection.execute(text('DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE username=:username)'),
                                   {"username": f"test_{suffix}_admin"})
                connection.execute(text('DELETE FROM admins WHERE user_id IN (SELECT id FROM users WHERE username=:username)'),
                                   {"username": f"test_{suffix}_admin"})
                connection.execute(text('DELETE FROM users WHERE username=:username'), {"username": f"test_{suffix}_admin"})
            engine.dispose()
