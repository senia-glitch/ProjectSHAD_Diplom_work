"""Opt-in: тесты, доски и блог через HTTP/WebSocket → core → event-infra → PostgreSQL.

Run with SHAD_RUN_DB_TESTS=1. Используется только отдельная TEST_DB_URL; созданные аккаунты удаляются,
их тесты, доски и записи блога удаляются каскадно.
"""
import os
import secrets

import pytest

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.getenv("SHAD_RUN_DB_TESTS") != "1", reason="Set SHAD_RUN_DB_TESTS=1")]

CHOICE_TASK = {"kind": "choice", "variant": "single", "prompt": "2 + 2 = ?", "points": 2,
               "data": {"options": ["3", "4", "5"]}, "answer": {"correct": [1]}}
OPEN_TASK = {"kind": "open", "variant": "short", "prompt": "Ваше имя", "points": 1, "data": {}}


def test_testing_boards_and_blog_on_postgresql(monkeypatch, tmp_path):
    from scripts.db_config import select_database
    from scripts.migrate import migrate
    # select_database подменяет DB_URL на тестовую; после теста окружение возвращается как было.
    for name in ("DB_URL", "DB_URL_ASYNC"):
        monkeypatch.delenv(name, raising=False)
    select_database(test=True)
    migrate()
    from fastapi.testclient import TestClient
    from core.scenario_registry import ScenarioRegistry
    from app.main import app
    # shutdown_core очищает реестр, а модули сценариев уже импортированы: восстановим его для следующих тестов.
    registered = dict(ScenarioRegistry._scenarios)
    monkeypatch.setattr(ScenarioRegistry, "_scenarios", registered)
    from app.utils import frontend_log

    monkeypatch.setattr(frontend_log, "LOG_FILE", tmp_path / "frontend.log")
    suffix, password, created = secrets.token_hex(5), secrets.token_hex(12), []

    with TestClient(app, raise_server_exceptions=False) as client:
        def request(method, path, actor=None, body=None, params=None, status=200):
            headers = {"Authorization": "Bearer " + actor["access_token"]} if actor else {}
            response = client.request(method, "/api/v1" + path, headers=headers, json=body, params=params)
            assert response.status_code == status, (method, path, response.status_code, response.text)
            return response.json() if response.content else None

        def register(role, name):
            account = request("POST", "/users/register", body={
                "role": role, "username": f"mod_{suffix}_{name}", "password": password,
                "full_name": f"Модуль {name}", "email": f"{suffix}_{name}@example.test"})
            created.append(account)
            return account

        try:
            tutor, student, stranger = register("tutor", "tutor"), register("student", "student"), \
                register("student", "stranger")
            request("POST", "/tutor/configurations", tutor, {"student_user_id": student["user_id"]})

            # ---------- тестирование ----------
            students = request("GET", "/testing/tutor/students", tutor)["items"]
            assert [s["id"] for s in students] == [student["user_id"]]
            quiz = request("POST", "/testing/tutor/tests", tutor, {
                "title": "Арифметика", "description": "**Проверка**", "tasks": [CHOICE_TASK, OPEN_TASK]}, status=201)
            qid = quiz["id"]
            request("GET", "/testing/tutor/tests", student, status=403)
            request("GET", f"/testing/student/tests/{qid}", student, status=404)
            request("PUT", f"/testing/tutor/tests/{qid}/access/{stranger['user_id']}", tutor, {"enabled": True},
                    status=404)  # не связан с репетитором
            request("PUT", f"/testing/tutor/tests/{qid}/access/{student['user_id']}", tutor, {"enabled": True})
            access = request("GET", f"/testing/tutor/tests/{qid}/access", tutor)["items"]
            assert [(a["student_id"], a["enabled"]) for a in access] == [(student["user_id"], True)]
            available = request("GET", "/testing/student/tests", student)["items"]
            assert [t["id"] for t in available] == [qid] and available[0]["owner_name"] == "Модуль tutor"
            opened = request("GET", f"/testing/student/tests/{qid}", student)
            assert all("answer" not in task for task in opened["tasks"])
            choice_id = opened["tasks"][0]["id"]
            right = opened["tasks"][0]["data"]["options"].index("4")
            attempt = request("POST", f"/testing/student/tests/{qid}/attempts", student, {
                "version": opened["version"], "answers": {choice_id: {"selected": [right]},
                                                          opened["tasks"][1]["id"]: {"text": "Аня"}}}, status=201)
            assert attempt["score"] == 2 and attempt["max_score"] == 2
            results = request("GET", f"/testing/tutor/tests/{qid}/results", tutor)["items"]
            assert [r["id"] for r in results] == [attempt["id"]]
            request("PUT", f"/testing/tutor/results/{attempt['id']}/review", tutor,
                    {"teacher_grade": "замечательно", "teacher_comment": "Отлично"})
            mine = request("GET", f"/testing/student/results/{attempt['id']}", student)
            assert mine["teacher_grade"] == "замечательно"
            request("GET", f"/testing/student/results/{attempt['id']}", stranger, status=404)

            # ---------- блог ----------
            draft = request("POST", "/blog/my/posts", tutor, {
                "title": "Как готовиться к ЕГЭ", "body": "# План\nТекст", "tags": ["ЕГЭ", "Математика"]}, status=201)
            assert draft["status"] == "draft" and draft["tags"] == ["егэ", "математика"]
            request("GET", f"/blog/posts/{draft['id']}", status=404)  # гость не видит черновик
            request("GET", f"/blog/posts/{draft['id']}", tutor)
            post = request("PUT", f"/blog/my/posts/{draft['id']}", tutor, {
                "title": "Как готовиться к ЕГЭ", "body": "# План\nТекст", "tags": ["егэ"], "status": "published"})
            assert post["published_at"]
            feed = request("GET", "/blog/posts", params={"author_id": tutor["user_id"], "tag": "егэ"})
            assert [p["id"] for p in feed["items"]] == [post["id"]]
            assert request("GET", f"/blog/authors/{tutor['user_id']}")["post_count"] == 1
            request("POST", f"/blog/posts/{post['id']}/comments", body={"text": "гость"}, status=401)
            comment = request("POST", f"/blog/posts/{post['id']}/comments", student, {"text": "Спасибо!"}, status=201)
            request("DELETE", f"/blog/comments/{comment['id']}", stranger, status=403)
            request("POST", "/blog/my/posts", student, {"title": "x"}, status=403)
            assert [c["text"] for c in request("GET", f"/blog/posts/{post['id']}/comments")["items"]] == ["Спасибо!"]
            request("DELETE", f"/blog/comments/{comment['id']}", tutor)

            # ---------- доски ----------
            board = request("POST", "/boards", tutor, {"title": "Урок 1"}, status=201)
            request("POST", "/boards", student, {"title": "нельзя"}, status=403)
            assert request("POST", "/boards/resolve", student, {"code": board["code"].lower()})["id"] == board["id"]
            with client.websocket_connect(f"/api/v1/boards/{board['id']}/ws") as ws:
                ws.send_json({"t": "hello", "token": student["access_token"], "code": board["code"]})
                init = ws.receive_json()
                assert init["t"] == "init" and init["you"]["name"] == "Модуль student"
                ws.send_json({"t": "stroke", "stroke": {"id": "stroke0001", "tool": "pen", "color": "#7177F8",
                                                        "width": 3, "pts": [0, 0, 10, 10]}})
                assert ws.receive_json()["t"] == "stroke"
            with client.websocket_connect(f"/api/v1/boards/{board['id']}/ws") as ws:
                ws.send_json({"t": "hello", "token": tutor["access_token"]})  # владелец входит без кода
                init = ws.receive_json()
                assert init["you"]["creator"] is True and len(init["strokes"]) == 1
            joined = request("GET", "/boards/joined", student)["items"]
            assert [b["id"] for b in joined] == [board["id"]]
            assert [b["id"] for b in request("GET", "/boards/mine", tutor)["items"]] == [board["id"]]
            request("DELETE", f"/boards/{board['id']}", student, status=403)
            request("DELETE", f"/boards/{board['id']}", tutor)
        finally:
            for account in reversed(created):
                client.post("/api/v1/users/me/delete", headers={"Authorization": "Bearer " + account["access_token"]},
                            json={})
