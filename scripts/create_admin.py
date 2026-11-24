"""Создание учётной записи администратора (открытая регистрация администраторов не создаёт).

Запускается при работающей БД после первого старта приложения (роли создаёт приложение):

    docker compose run --rm -it migrate python -m scripts.create_admin --username admin --email admin@example.com

Пароль вводится скрытно дважды; в автоматизации его можно передать переменной SHAD_ADMIN_PASSWORD.
Существующие пользователи не изменяются.
"""
import argparse
import asyncio
import getpass
import os
import secrets
import string
import sys

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import create_engine, text

from scripts.db_config import select_database


def read_password() -> str:
    from app.utils.validation import PasswordStr
    password = os.getenv("SHAD_ADMIN_PASSWORD")
    if password is None:
        password = getpass.getpass("Пароль администратора: ")
        if getpass.getpass("Повторите пароль: ") != password:
            sys.exit("Пароли не совпадают")
    try:
        return TypeAdapter(PasswordStr).validate_python(password)
    except ValidationError:
        sys.exit("Пароль: от 8 до 72 байт")


def personal_number() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "IND-" + "".join(secrets.choice(alphabet) for _ in range(8))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", default="Администратор")
    args = parser.parse_args()

    password = read_password()
    from core.utils.security import hash_password
    password_hash = asyncio.run(hash_password(password))

    engine = create_engine(select_database(), hide_parameters=True)
    try:
        with engine.begin() as connection:
            role = connection.execute(text("SELECT id FROM roles WHERE name = 'admin'")).scalar()
            if role is None:
                sys.exit("Роли ещё не созданы: запустите приложение один раз и повторите")
            taken = connection.execute(text("SELECT 1 FROM users WHERE username = :u OR email = :e"),
                                       {"u": args.username, "e": args.email}).first()
            if taken:
                sys.exit("Логин или почта уже заняты; существующие пользователи не изменяются")
            user_id = connection.execute(text(
                "INSERT INTO users (role_id, username, personal_number, password_hash, full_name, email, created_at) "
                "VALUES (:role, :u, :pn, :ph, :name, :e, now()) RETURNING id"),
                {"role": role, "u": args.username, "pn": personal_number(), "ph": password_hash,
                 "name": args.full_name, "e": args.email}).scalar_one()
            connection.execute(text("INSERT INTO admins (user_id) VALUES (:id)"), {"id": user_id})
    finally:
        engine.dispose()
    print(f"Администратор {args.username} создан")


if __name__ == "__main__":
    main()
