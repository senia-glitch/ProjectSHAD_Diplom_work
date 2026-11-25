"""Личный блог репетитора: записи в Markdown, черновики, теги, закрепление и комментарии.

Опубликованные записи читают все, включая гостей. Черновик видит только автор.
Комментарии пишут вошедшие пользователи; удаляет автор комментария, автор записи или администратор.
"""
import json
import re
from datetime import datetime, timezone
from typing import Literal

from core import BaseScenario, NotFoundError, register_scenario
from pydantic import BaseModel, Field, field_validator

from app.core.exceptions import ForbiddenError
from app.utils.notifications import notify_user

MAX_TAGS = 8
TAG_RE = re.compile(r'^[\w\- +#.]{1,32}$')
PAGE_LIMIT = 50


def _now():
    return datetime.now(timezone.utc)


def _clean_tags(values: list[str]) -> list[str]:
    seen, result = set(), []
    for raw in values:
        tag = ' '.join(str(raw).split()).lower()
        if not tag:
            continue
        if not TAG_RE.match(tag):
            raise ValueError(f'Тег «{tag[:32]}» содержит недопустимые символы')
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    if len(result) > MAX_TAGS:
        raise ValueError(f'Не больше {MAX_TAGS} тегов')
    return result


def _tags(value) -> list[str]:
    try:
        parsed = json.loads(value or '[]')
        return [t for t in parsed if isinstance(t, str)]
    except (TypeError, ValueError):
        return []


# ---------- DTO ----------

class PostInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default='', max_length=50000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: Literal['draft', 'published'] = 'draft'
    pinned: bool = False

    @field_validator('title')
    @classmethod
    def _title(cls, value):
        value = ' '.join(value.split())
        if not value:
            raise ValueError('Укажите заголовок')
        return value

    @field_validator('tags')
    @classmethod
    def _tags(cls, value):
        return _clean_tags(value)


class CreatePostDTO(PostInput):
    actor_id: int = Field(gt=0)


class UpdatePostDTO(PostInput):
    actor_id: int = Field(gt=0)
    post_id: int = Field(gt=0)


class OwnPostDTO(BaseModel):
    actor_id: int = Field(gt=0)
    post_id: int = Field(gt=0)


class ActorDTO(BaseModel):
    actor_id: int = Field(gt=0)


class FeedDTO(BaseModel):
    author_id: int | None = Field(default=None, gt=0)
    # Только записи владельца платформы (администраторов) — лента главной страницы.
    owner: bool = False
    tag: str | None = Field(default=None, max_length=32)
    # Поиск по названию записи (без учёта регистра).
    q: str | None = Field(default=None, max_length=100)
    viewer_id: int | None = None
    limit: int = Field(default=20, ge=1, le=PAGE_LIMIT)
    offset: int = Field(default=0, ge=0)


class ViewPostDTO(BaseModel):
    viewer_id: int | None = None
    post_id: int = Field(gt=0)


class PostRefDTO(BaseModel):
    post_id: int = Field(gt=0)


class CommentDTO(BaseModel):
    actor_id: int = Field(gt=0)
    post_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=3000)
    # Ответ на комментарий этой же записи (ветка одного уровня).
    parent_id: int | None = Field(default=None, gt=0)

    @field_validator('text')
    @classmethod
    def _text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Напишите комментарий')
        return value


class DeleteCommentDTO(BaseModel):
    actor_id: int = Field(gt=0)
    actor_role: str
    comment_id: int = Field(gt=0)


class AuthorRefDTO(BaseModel):
    author_id: int = Field(gt=0)


# ---------- ответы ----------

class PostItem(BaseModel):
    id: int
    author_id: int
    author_name: str
    title: str
    body: str
    tags: list[str]
    status: str
    pinned: bool
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    comment_count: int = 0
    like_count: int = 0
    liked: bool = False
    author_avatar: str | None = None
    # Запись владельца платформы (администратора): ссылки ведут на главную, а не в блог репетитора.
    owner: bool = False


class PostList(BaseModel):
    items: list[PostItem]
    total: int


class TagCount(BaseModel):
    tag: str
    count: int


class AuthorItem(BaseModel):
    id: int
    full_name: str
    avatar_url: str | None = None
    post_count: int
    last_published_at: datetime | None


class AuthorList(BaseModel):
    items: list[AuthorItem]


class BlogAuthor(BaseModel):
    id: int
    full_name: str
    avatar_url: str | None = None
    about: str | None
    post_count: int
    tags: list[TagCount]


class CommentItem(BaseModel):
    id: int
    post_id: int
    author_id: int
    author_name: str
    author_role: str
    author_avatar: str | None = None
    parent_id: int | None = None
    text: str
    created_at: datetime


class CommentList(BaseModel):
    items: list[CommentItem]


class Done(BaseModel):
    ok: bool = True


class LikeDTO(BaseModel):
    actor_id: int = Field(gt=0)
    post_id: int = Field(gt=0)


class LikeResult(BaseModel):
    liked: bool
    like_count: int


SELECT_POST = (
    'SELECT p.*, u.full_name AS author_name, '
    '(SELECT count(*) FROM blog_comments c WHERE c.post_id = p.id) AS comment_count, '
    '(SELECT count(*) FROM blog_post_likes k WHERE k.post_id = p.id) AS like_count, '
    'u.avatar_url AS author_avatar, '
    'EXISTS (SELECT 1 FROM admins a WHERE a.user_id = p.author_id) AS owner '
    'FROM blog_posts p JOIN users u ON u.id = p.author_id ')


def _item(row) -> PostItem:
    return PostItem(**{k: row[k] for k in ('id', 'author_id', 'author_name', 'title', 'body', 'status', 'pinned',
                                           'created_at', 'updated_at', 'published_at', 'comment_count')},
                    owner=bool(row.get('owner')),
                    like_count=int(row.get('like_count') or 0),
                    author_avatar=row.get('author_avatar'),
                    tags=_tags(row['tags']))


async def _mark_liked(db, items: list, viewer_id: int | None) -> list:
    """Отметить записи, которые нравятся читателю (гость — ни одной)."""
    if not viewer_id or not items:
        return items
    ids = [i.id for i in items]
    rows = await db.query(
        'SELECT post_id FROM blog_post_likes WHERE user_id = :u AND post_id = ANY(:ids)', {'u': viewer_id, 'ids': ids})
    liked = {r['post_id'] for r in rows}
    for item in items:
        item.liked = item.id in liked
    return items


async def _own(db, actor_id, post_id):
    row = await db.read('blog_posts', post_id)
    if row is None or row['author_id'] != actor_id:
        raise NotFoundError('Запись не найдена')
    return row


async def _load(db, post_id):
    rows = await db.query(SELECT_POST + 'WHERE p.id = :id', {'id': post_id})
    if not rows:
        raise NotFoundError('Запись не найдена')
    return rows[0]


# ---------- репетитор: свои записи ----------

@register_scenario('blog.create', dto=CreatePostDTO, response=PostItem)
class CreatePost(BaseScenario):
    async def execute(self, dto):
        stamp = _now()
        row = await self._db.create('blog_posts', {
            'author_id': dto.actor_id, 'title': dto.title, 'body': dto.body.strip(),
            'tags': json.dumps(dto.tags, ensure_ascii=False), 'status': dto.status, 'pinned': dto.pinned,
            'created_at': stamp, 'updated_at': stamp,
            'published_at': stamp if dto.status == 'published' else None})
        return _item(await _load(self._db, row['id']))


@register_scenario('blog.update', dto=UpdatePostDTO, response=PostItem)
class UpdatePost(BaseScenario):
    async def execute(self, dto):
        row = await _own(self._db, dto.actor_id, dto.post_id)
        stamp = _now()
        # Дата публикации — момент первой публикации; снятие с публикации её сбрасывает.
        published_at = (row['published_at'] or stamp) if dto.status == 'published' else None
        await self._db.update('blog_posts', dto.post_id, {
            'title': dto.title, 'body': dto.body.strip(), 'tags': json.dumps(dto.tags, ensure_ascii=False),
            'status': dto.status, 'pinned': dto.pinned, 'updated_at': stamp, 'published_at': published_at})
        return _item(await _load(self._db, dto.post_id))


@register_scenario('blog.delete', dto=OwnPostDTO, response=Done)
class DeletePost(BaseScenario):
    async def execute(self, dto):
        await _own(self._db, dto.actor_id, dto.post_id)
        await self._db.delete('blog_posts', dto.post_id)  # комментарии удаляются каскадно
        return Done()


@register_scenario('blog.list_mine', dto=ActorDTO, response=PostList)
class ListMyPosts(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(
            SELECT_POST + 'WHERE p.author_id = :a ORDER BY p.pinned DESC, p.updated_at DESC, p.id DESC',
            {'a': dto.actor_id})
        return PostList(items=[_item(r) for r in rows], total=len(rows))


# ---------- публичное чтение ----------

@register_scenario('blog.feed', dto=FeedDTO, response=PostList)
class Feed(BaseScenario):
    """Лента опубликованных записей: все репетиторы или один автор, с фильтром по тегу."""
    async def execute(self, dto):
        where, params = ["p.status = 'published'"], {'lim': dto.limit, 'off': dto.offset}
        if dto.author_id:
            where.append('p.author_id = :a')
            params['a'] = dto.author_id
        if dto.owner:
            where.append('p.author_id IN (SELECT user_id FROM admins)')
        elif not dto.author_id:
            # Раздел «Блог» — записи репетиторов; блог владельца живёт на главной.
            where.append('p.author_id NOT IN (SELECT user_id FROM admins)')
        if dto.q and dto.q.strip():
            # % и _ из запроса ищутся буквально: экранируем их символом «!».
            needle = ' '.join(dto.q.split()).replace('!', '!!').replace('%', '!%').replace('_', '!_')
            where.append("p.title ILIKE :q ESCAPE '!'")
            params['q'] = f'%{needle}%'
        if dto.tag:
            where.append('CAST(p.tags AS jsonb) @> CAST(:tag AS jsonb)')
            params['tag'] = json.dumps([' '.join(dto.tag.split()).lower()], ensure_ascii=False)
        condition = ' AND '.join(where)
        # Закреплённые записи поднимаются только в ленте конкретного автора.
        order = 'p.pinned DESC, ' if dto.author_id or dto.owner else ''
        rows = await self._db.query(
            SELECT_POST + f'WHERE {condition} ORDER BY {order}p.published_at DESC, p.id DESC LIMIT :lim OFFSET :off',
            params)
        total = await self._db.query(f'SELECT count(*) AS n FROM blog_posts p WHERE {condition}', params)
        items = await _mark_liked(self._db, [_item(r) for r in rows], dto.viewer_id)
        return PostList(items=items, total=total[0]['n'])


@register_scenario('blog.get', dto=ViewPostDTO, response=PostItem)
class GetPost(BaseScenario):
    async def execute(self, dto):
        row = await _load(self._db, dto.post_id)
        if row['status'] != 'published' and row['author_id'] != dto.viewer_id:
            raise NotFoundError('Запись не найдена')
        return (await _mark_liked(self._db, [_item(row)], dto.viewer_id))[0]


@register_scenario('blog.authors', dto=None, response=AuthorList)
class Authors(BaseScenario):
    """Репетиторы, у которых есть опубликованные записи."""
    async def execute(self, dto):
        rows = await self._db.query(
            "SELECT u.id, u.full_name, u.avatar_url, count(p.id) AS post_count, max(p.published_at) AS last_published_at "
            "FROM blog_posts p JOIN users u ON u.id = p.author_id WHERE p.status = 'published' "
            "AND u.id NOT IN (SELECT user_id FROM admins) "
            "GROUP BY u.id, u.full_name, u.avatar_url ORDER BY max(p.published_at) DESC", {})
        return AuthorList(items=[AuthorItem(**r) for r in rows])


@register_scenario('blog.author', dto=AuthorRefDTO, response=BlogAuthor)
class Author(BaseScenario):
    """Шапка блога репетитора: имя, «о себе» из профиля, число записей и теги."""
    async def execute(self, dto):
        rows = await self._db.query(
            "SELECT u.id, u.full_name, u.avatar_url, u.additional_info AS about FROM users u "
            "JOIN tutors t ON t.user_id = u.id WHERE u.id = :a", {'a': dto.author_id})
        if not rows:
            raise NotFoundError('Блог не найден')
        posts = await self._db.query(
            "SELECT tags FROM blog_posts WHERE author_id = :a AND status = 'published'", {'a': dto.author_id})
        counts: dict[str, int] = {}
        for post in posts:
            for tag in _tags(post['tags']):
                counts[tag] = counts.get(tag, 0) + 1
        tags = [TagCount(tag=t, count=n) for t, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]
        return BlogAuthor(**rows[0], post_count=len(posts), tags=tags)


# ---------- комментарии ----------

COMMENT_SELECT = (
    'SELECT c.*, u.full_name AS author_name, u.avatar_url AS author_avatar, r.name AS author_role FROM blog_comments c '
    'JOIN users u ON u.id = c.author_id JOIN roles r ON r.id = u.role_id ')


async def _published(db, post_id):
    row = await db.read('blog_posts', post_id)
    if row is None or row['status'] != 'published':
        raise NotFoundError('Запись не найдена')
    return row


@register_scenario('blog.comments', dto=PostRefDTO, response=CommentList)
class Comments(BaseScenario):
    async def execute(self, dto):
        await _published(self._db, dto.post_id)
        rows = await self._db.query(COMMENT_SELECT + 'WHERE c.post_id = :p ORDER BY c.id', {'p': dto.post_id})
        return CommentList(items=[CommentItem(**r) for r in rows])


@register_scenario('blog.comment_create', dto=CommentDTO, response=CommentItem)
class CreateComment(BaseScenario):
    async def execute(self, dto):
        post = await _published(self._db, dto.post_id)
        parent = None
        if dto.parent_id:
            found = await self._db.query(
                'SELECT id, post_id, parent_id, author_id FROM blog_comments WHERE id = :id', {'id': dto.parent_id})
            if not found or found[0]['post_id'] != dto.post_id:
                raise NotFoundError('Комментарий не найден')
            parent = found[0]
        # Ветка одного уровня: ответ на ответ крепится к исходному комментарию.
        parent_id = (parent['parent_id'] or parent['id']) if parent else None
        row = await self._db.create('blog_comments', {
            'post_id': dto.post_id, 'author_id': dto.actor_id, 'text': dto.text, 'created_at': _now(),
            'parent_id': parent_id})
        rows = await self._db.query(COMMENT_SELECT + 'WHERE c.id = :id', {'id': row['id']})
        item = CommentItem(**rows[0])
        title = post['title'][:80]
        if parent and parent['author_id'] != dto.actor_id:
            await notify_user(self._db, parent['author_id'], 'blog_reply',
                              f'{item.author_name} ответил(а) на ваш комментарий к записи «{title}»')
        elif not parent and post['author_id'] != dto.actor_id:
            await notify_user(self._db, post['author_id'], 'blog_comment',
                              f'{item.author_name} прокомментировал(а) вашу запись «{title}»')
        return item


@register_scenario('blog.comment_delete', dto=DeleteCommentDTO, response=Done)
class DeleteComment(BaseScenario):
    async def execute(self, dto):
        rows = await self._db.query(
            'SELECT c.author_id, p.author_id AS post_author FROM blog_comments c '
            'JOIN blog_posts p ON p.id = c.post_id WHERE c.id = :id', {'id': dto.comment_id})
        if not rows:
            raise NotFoundError('Комментарий не найден')
        row = rows[0]
        if dto.actor_role != 'admin' and dto.actor_id not in (row['author_id'], row['post_author']):
            raise ForbiddenError('Удалить комментарий может его автор или автор записи')
        await self._db.delete('blog_comments', dto.comment_id)
        return Done()


# ---------- отметки «нравится» ----------

@register_scenario('blog.like', dto=LikeDTO, response=LikeResult)
class ToggleLike(BaseScenario):
    """Нажатие «нравится»: ставит отметку или снимает уже поставленную."""
    async def execute(self, dto):
        await _published(self._db, dto.post_id)
        removed = await self._db.query(
            'DELETE FROM blog_post_likes WHERE post_id = :p AND user_id = :u RETURNING post_id',
            {'p': dto.post_id, 'u': dto.actor_id}, channel='write')
        if not removed:
            await self._db.query(
                'INSERT INTO blog_post_likes (post_id, user_id, created_at) VALUES (:p, :u, :t) '
                'ON CONFLICT DO NOTHING', {'p': dto.post_id, 'u': dto.actor_id, 't': _now()}, channel='write')
        count = await self._db.query('SELECT count(*) AS n FROM blog_post_likes WHERE post_id = :p', {'p': dto.post_id})
        return LikeResult(liked=not removed, like_count=int(count[0]['n']))
