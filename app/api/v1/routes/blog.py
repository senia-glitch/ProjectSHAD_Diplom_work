"""Внешние сценарии блога: публичное чтение, записи репетитора и комментарии."""
from core import run
from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import BaseModel, Field

from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.blog.posts import (ActorDTO, AuthorList, AuthorRefDTO, BlogAuthor, CommentDTO, CommentItem,
                                      CommentList, CreatePostDTO, DeleteCommentDTO, Done, FeedDTO, LikeDTO,
                                      LikeResult, OwnPostDTO, PostInput, PostItem, PostList, PostRefDTO,
                                      UpdatePostDTO, ViewPostDTO)

router = APIRouter(prefix='/blog', tags=['blog'])


class CommentBody(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    parent_id: int | None = Field(default=None, gt=0)


def _viewer(request: Request) -> int | None:
    principal = getattr(request.state, 'principal', None) or {}
    return principal.get('user_id')


# ---------- публичное чтение (в том числе гостем) ----------

@router.get('/posts', response_model=PostList)
@external_scenario('blog.feed', core='blog.feed')
async def feed(request: Request, author_id: int | None = Query(default=None, gt=0),
               tag: str | None = Query(default=None, max_length=32), q: str | None = Query(default=None, max_length=100),
               owner: bool = False,
               limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0)):
    return await run('blog.feed', FeedDTO(author_id=author_id, tag=tag, q=q, owner=owner, viewer_id=_viewer(request),
                                          limit=limit, offset=offset))


@router.get('/posts/{post_id}', response_model=PostItem)
@external_scenario('blog.read', core='blog.get')
async def get_post(request: Request, post_id: int = Path(gt=0)):
    return await run('blog.get', ViewPostDTO(viewer_id=_viewer(request), post_id=post_id))


@router.get('/posts/{post_id}/comments', response_model=CommentList)
@external_scenario('blog.comments', core='blog.comments')
async def comments(post_id: int = Path(gt=0)):
    return await run('blog.comments', PostRefDTO(post_id=post_id))


@router.get('/authors', response_model=AuthorList)
@external_scenario('blog.authors', core='blog.authors')
async def authors():
    return await run('blog.authors', None)


@router.get('/authors/{author_id}', response_model=BlogAuthor)
@external_scenario('blog.author', core='blog.author')
async def author(author_id: int = Path(gt=0)):
    return await run('blog.author', AuthorRefDTO(author_id=author_id))


# ---------- комментарии (вошедшие пользователи) ----------

@router.post('/posts/{post_id}/comments', status_code=201, response_model=CommentItem)
@external_scenario('blog.comment', core='blog.comment_create')
async def add_comment(body: CommentBody, post_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('blog.comment_create', CommentDTO(actor_id=user['user_id'], post_id=post_id, text=body.text,
                                                       parent_id=body.parent_id))


@router.post('/posts/{post_id}/like', response_model=LikeResult)
@external_scenario('blog.like', core='blog.like')
async def like(post_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('blog.like', LikeDTO(actor_id=user['user_id'], post_id=post_id))


@router.delete('/comments/{comment_id}', response_model=Done)
@external_scenario('blog.comment_delete', core='blog.comment_delete')
async def delete_comment(comment_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('blog.comment_delete', DeleteCommentDTO(actor_id=user['user_id'], actor_role=user['role'],
                                                             comment_id=comment_id))


# ---------- записи репетитора ----------

@router.get('/my/posts', response_model=PostList)
@external_scenario('blog.list_mine', core='blog.list_mine')
async def my_posts(user: dict = Depends(get_current_user)):
    return await run('blog.list_mine', ActorDTO(actor_id=user['user_id']))


@router.post('/my/posts', status_code=201, response_model=PostItem)
@external_scenario('blog.create', core='blog.create')
async def create_post(body: PostInput, user: dict = Depends(get_current_user)):
    return await run('blog.create', CreatePostDTO(**body.model_dump(), actor_id=user['user_id']))


@router.put('/my/posts/{post_id}', response_model=PostItem)
@external_scenario('blog.update', core='blog.update')
async def update_post(body: PostInput, post_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('blog.update', UpdatePostDTO(**body.model_dump(), actor_id=user['user_id'], post_id=post_id))


@router.delete('/my/posts/{post_id}', response_model=Done)
@external_scenario('blog.delete', core='blog.delete')
async def delete_post(post_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('blog.delete', OwnPostDTO(actor_id=user['user_id'], post_id=post_id))
