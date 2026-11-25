# Правила комментариев блога: один комментарий читателя к записи, отвечает только автор — один раз.
# Запуск: pytest tests/test_blog_comment_rules.py -q
import asyncio
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core import ConflictError, NotFoundError

from app.core.exceptions import ForbiddenError
from app.scenarios.blog.posts import CommentDTO, CreateComment

AUTHOR, READER, OTHER = 10, 20, 30


class Stub:
    """Запись 1 автора 10. Комментарии: id → (author_id, parent_id)."""

    def __init__(self, comments=None):
        self.comments = dict(comments or {})
        self.notified = []

    async def read(self, table, rid):
        assert table == 'blog_posts'
        return {'id': 1, 'author_id': AUTHOR, 'status': 'published', 'title': 'Запись'}

    async def query(self, sql, params, **kw):
        if 'SELECT id, post_id, parent_id, author_id FROM blog_comments' in sql:
            c = self.comments.get(params['id'])
            return [{'id': params['id'], 'post_id': 1, 'parent_id': c[1], 'author_id': c[0]}] if c else []
        if 'WHERE parent_id = :p' in sql:
            return [1] if any(p == params['p'] for _, p in self.comments.values()) else []
        if 'author_id = :a AND parent_id IS NULL' in sql:
            return [1] if any(a == params['a'] and p is None for a, p in self.comments.values()) else []
        if 'FROM blog_comments c' in sql:  # выборка созданного комментария
            cid = params['id']
            a, p = self.comments[cid]
            return [{'id': cid, 'post_id': 1, 'author_id': a, 'author_name': f'user{a}', 'author_role': 'student',
                     'author_avatar': None, 'parent_id': p, 'text': 't',
                     'created_at': datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc)}]
        return []

    async def create(self, table, data):
        if table == 'notifications':
            self.notified.append(data)
            return data
        cid = max(self.comments or {0: 0}) + 1
        self.comments[cid] = (data['author_id'], data['parent_id'])
        return {'id': cid}


def comment(db, actor, parent=None):
    return asyncio.run(CreateComment(db=db).execute(CommentDTO(actor_id=actor, post_id=1, text='привет', parent_id=parent)))


def test_reader_writes_one_comment_only():
    db = Stub()
    comment(db, READER)
    with pytest.raises(ConflictError):
        comment(db, READER)
    comment(db, OTHER)  # другой читатель — может


def test_author_cannot_comment_own_post_but_replies_once():
    db = Stub({1: (READER, None)})
    with pytest.raises(ConflictError):
        comment(db, AUTHOR)
    reply = comment(db, AUTHOR, parent=1)
    assert reply.parent_id == 1
    with pytest.raises(ConflictError):
        comment(db, AUTHOR, parent=1)


def test_only_author_replies_and_only_to_top_level_comments():
    db = Stub({1: (READER, None), 2: (AUTHOR, 1)})
    with pytest.raises(ForbiddenError):
        comment(db, OTHER, parent=1)
    with pytest.raises(NotFoundError):
        comment(db, AUTHOR, parent=2)  # ответ на ответ
