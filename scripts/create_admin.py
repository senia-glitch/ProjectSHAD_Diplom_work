"""Администратор (владелец) и его ключ входа.

Вход администратора — только по уникальному ключу на странице /admin/login; пароль у
учётной записи владельца случайный и не используется. Ключ печатается один раз, в БД
хранится только его SHA-256. Запуск при работающей БД после первого старта приложения:

    # новый администратор + ключ
    docker compose run --rm migrate python -m scripts.create_admin --username owner --email owner@example.ru
    # потеряли ключ — выпустить новый (старый сразу перестаёт действовать)
    docker compose run --rm migrate python -m scripts.create_admin --username owner --rotate

Существующие пользователи не меняются (кроме ключа при --rotate).
"""
import argparse
import asyncio
import secrets
import string
import sys

from sqlalchemy import create_engine, text

from app.utils.admin_audit import hash_admin_key, new_admin_key
from app.utils.clock import utc_now
from scripts.db_config import select_database


def personal_number() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "IND-" + "".join(secrets.choice(alphabet) for _ in range(8))


def print_key(username: str, key: str) -> None:
    print(f"Ключ администратора {username} (сохраните сейчас — повторно его не показать):")
    print()
    print(f"    {key}")
    print()
    print("Вход: страница /admin/login.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email")
    parser.add_argument("--full-name", default="Владелец")
    parser.add_argument("--rotate", action="store_true", help="выпустить новый ключ существующему администратору")
    args = parser.parse_args()

    key, now = new_admin_key(), utc_now().replace(microsecond=0)
    engine = create_engine(select_database(), hide_parameters=True)
    try:
        with engine.begin() as connection:
            if args.rotate:
                row = connection.execute(text(
                    'SELECT a.id FROM "admins" a JOIN "users" u ON u.id = a.user_id WHERE u.username = :u'),
                    {"u": args.username}).first()
                if row is None:
                    sys.exit("Администратор с таким логином не найден")
                connection.execute(text('UPDATE "admins" SET key_hash = :h, key_created_at = :t WHERE id = :id'),
                                   {"h": hash_admin_key(key), "t": now, "id": row.id})
                print_key(args.username, key)
                return

            if not args.email:
                sys.exit("Укажите --email для нового администратора")
            role = connection.execute(text("SELECT id FROM roles WHERE name = 'admin'")).scalar()
            if role is None:
                sys.exit("Роли ещё не созданы: запустите приложение один раз и повторите")
            taken = connection.execute(text("SELECT 1 FROM users WHERE username = :u OR email = :e"),
                                       {"u": args.username, "e": args.email}).first()
            if taken:
                sys.exit("Логин или почта уже заняты; существующие пользователи не изменяются")
            from core.utils.security import hash_password
            # Пароль владельца не используется (вход только по ключу): случайный и нигде не показан.
            unusable = asyncio.run(hash_password(secrets.token_urlsafe(32)))
            user_id = connection.execute(text(
                "INSERT INTO users (role_id, username, personal_number, password_hash, full_name, email, created_at) "
                "VALUES (:role, :u, :pn, :ph, :name, :e, :t) RETURNING id"),
                {"role": role, "u": args.username, "pn": personal_number(), "ph": unusable,
                 "name": args.full_name, "e": args.email, "t": now}).scalar_one()
            connection.execute(text("INSERT INTO admins (user_id, key_hash, key_created_at) VALUES (:id, :h, :t)"),
                               {"id": user_id, "h": hash_admin_key(key), "t": now})
    finally:
        engine.dispose()
    print(f"Администратор {args.username} создан")
    print_key(args.username, key)


if __name__ == "__main__":
    main()
