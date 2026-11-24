"""Демо-данные через HTTP API запущенного приложения: репетитор, ученик, связь, тест, запись блога и доска.

Запуск (приложение уже работает):
    .\\venv\\Scripts\\python.exe -m scripts.seed_demo --api http://127.0.0.1:8000

Повторный запуск не дублирует аккаунты: существующие входят по паролю. Пароль — DEMO_PASSWORD
(по умолчанию demo12345). Только для локальной разработки.
"""
import argparse
import os

import httpx

PASSWORD = os.getenv("DEMO_PASSWORD", "demo12345")
ACCOUNTS = {
    "tutor": {"username": "demo_tutor", "full_name": "Анна Репетитор", "email": "demo_tutor@example.test"},
    "student": {"username": "demo_student", "full_name": "Илья Ученик", "email": "demo_student@example.test"},
}
QUIZ = {
    "title": "Дроби: разминка",
    "description": "Короткая проверка перед занятием. **Удачи!**",
    "tasks": [
        {"kind": "choice", "variant": "single", "prompt": "Сколько будет 1/2 + 1/4?", "points": 2,
         "data": {"options": ["3/4", "2/6", "1/6"]}, "answer": {"correct": [0]}},
        {"kind": "ordering", "variant": "vertical", "prompt": "Расположите по возрастанию", "points": 2,
         "data": {"items": ["1/8", "1/4", "1/2", "1"]}, "answer": None},
        {"kind": "open", "variant": "long", "prompt": "Объясните, как сравнить 2/3 и 3/5.", "points": 3, "data": {}},
    ],
}
POST = {
    "title": "Как подготовиться к первому занятию",
    "body": "## Что взять с собой\n\n- тетрадь в клетку\n- список вопросов\n\n> Перед уроком пройдите разминку в разделе «Тесты».\n",
    "tags": ["советы", "математика"],
    "status": "published",
    "pinned": True,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    client = httpx.Client(base_url=args.api.rstrip("/") + "/api/v1", timeout=30)

    def account(role):
        info = ACCOUNTS[role]
        response = client.post("/auth/login", json={"username": info["username"], "password": PASSWORD})
        if response.status_code != 200:
            response = client.post("/users/register", json={"role": role, "password": PASSWORD, **info})
            response.raise_for_status()
        data = response.json()
        return {"id": data["user_id"], "headers": {"Authorization": "Bearer " + data["access_token"]}}

    tutor, student = account("tutor"), account("student")
    linked = client.get("/testing/tutor/students", headers=tutor["headers"]).json()["items"]
    if not any(s["id"] == student["id"] for s in linked):
        client.post("/tutor/configurations", headers=tutor["headers"],
                    json={"student_user_id": student["id"]}).raise_for_status()
    quizzes = client.get("/testing/tutor/tests", headers=tutor["headers"]).json()["items"]
    quiz = next((q for q in quizzes if q["title"] == QUIZ["title"]), None)
    if quiz is None:
        quiz = client.post("/testing/tutor/tests", headers=tutor["headers"], json=QUIZ)
        quiz.raise_for_status()
        quiz = quiz.json()
    client.put(f"/testing/tutor/tests/{quiz['id']}/access/{student['id']}", headers=tutor["headers"],
               json={"enabled": True}).raise_for_status()
    posts = client.get("/blog/my/posts", headers=tutor["headers"]).json()["items"]
    if not any(p["title"] == POST["title"] for p in posts):
        client.post("/blog/my/posts", headers=tutor["headers"], json=POST).raise_for_status()
    boards = client.get("/boards/mine", headers=tutor["headers"]).json()["items"]
    code = None
    if not boards:
        board = client.post("/boards", headers=tutor["headers"], json={"title": "Демо-доска"})
        board.raise_for_status()
        code = board.json()["code"]
    print("Демо-аккаунты: demo_tutor / demo_student (пароль из DEMO_PASSWORD, по умолчанию demo12345).")
    if code:
        print(f"Код демо-доски: {code}")


if __name__ == "__main__":
    main()
