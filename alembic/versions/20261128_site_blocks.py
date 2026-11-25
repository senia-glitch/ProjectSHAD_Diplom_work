"""Guest landing page built from blocks editable in the admin panel.

Revision ID: 20261128_site_blocks
Revises: 20261127_social
"""
import json
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20261128_site_blocks"
down_revision = "20261127_social"
branch_labels = None
depends_on = None

# Начальное содержимое — тексты прежней главной страницы для гостей.
DEFAULT_BLOCKS = [
    ("hero", "Больше времени на сами занятия",
     "Расписание, запись на уроки и связь с репетитором — в одном спокойном рабочем пространстве.",
     [{"title": "Единое расписание занятий", "body": ""},
      {"title": "Удобная запись на свободное время", "body": ""},
      {"title": "Участники, ссылки и оплаты рядом", "body": ""}]),
    ("features", "Что умеет SHAD", "",
     [{"title": "Видеть всю неделю",
       "body": "Занятия и свободные окна в наглядном расписании. Переключайтесь между неделей и календарём."},
      {"title": "Оставаться на связи",
       "body": "Ученики и репетиторы, персональные условия и ссылки на занятия в одном месте."},
      {"title": "Планировать без суеты",
       "body": "Репетитор открывает удобные часы, ученик выбирает подходящее время для записи."}]),
    ("cta", "Попробуйте бесплатно", "Регистрация занимает минуту. Репетитор и ученик работают в одном кабинете.", []),
]


def upgrade():
    table = op.create_table(
        "site_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("items", sa.Text(), server_default="[]", nullable=False),
        sa.Column("visible", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(table, [
        {"position": i, "kind": kind, "title": title, "body": body,
         "items": json.dumps(items, ensure_ascii=False), "visible": True, "updated_at": now}
        for i, (kind, title, body, items) in enumerate(DEFAULT_BLOCKS)
    ])


def downgrade():
    op.drop_table("site_blocks")
