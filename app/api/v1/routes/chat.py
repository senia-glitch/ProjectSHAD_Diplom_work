"""Личный чат: REST для истории и запасной отправки, WebSocket для живой переписки."""
import asyncio
import json
import logging

from core import CoreError, run
from fastapi import APIRouter, Depends, Path, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from app.api.access import authenticate, external_scenario
from app.api.v1.dependencies import get_current_user
from app.api.v1.routes.boards import origin_allowed
from app.realtime.chat_hub import ChatConn, chat_hub
from app.realtime.hub import RateLimiter, hub as board_hub
from app.scenarios.chat.messages import (TEXT_MAX, DialogDTO, DialogList, HistoryDTO, MeDTO, MessageList, ReadResult,
                                         SendDTO, SendResult, UnreadCount)

router = APIRouter(prefix='/chat', tags=['chat'])
log = logging.getLogger('app.chat')
CLOSE_FORBIDDEN, CLOSE_POLICY = 4403, 1008


class TextBody(BaseModel):
    text: str = Field(min_length=1, max_length=TEXT_MAX)


async def deliver(result: SendResult):
    """Новое сообщение — во все вкладки получателя и отправителя."""
    event = {'t': 'message', 'message': result.message.model_dump(mode='json')}
    chat_hub.push(result.recipient_id, event)
    chat_hub.push(result.message.sender_id, event)


def notify_read(me_id: int, result: ReadResult):
    if result.count:
        # Собеседник видит «прочитано», у читателя в других вкладках снимается счётчик.
        chat_hub.push(result.partner_id, {'t': 'read', 'by': me_id})
        chat_hub.push(me_id, {'t': 'read_self', 'partner_id': result.partner_id})


# ---------- REST ----------

@router.get('/dialogs', response_model=DialogList)
@external_scenario('chat.dialogs', core='chat.dialogs')
async def dialogs(user: dict = Depends(get_current_user)):
    return await run('chat.dialogs', MeDTO(me_id=user['user_id']))


@router.get('/unread', response_model=UnreadCount)
@external_scenario('chat.unread', core='chat.unread')
async def unread(user: dict = Depends(get_current_user)):
    return await run('chat.unread', MeDTO(me_id=user['user_id']))


@router.get('/dialogs/{partner_id}/messages', response_model=MessageList)
@external_scenario('chat.messages', core='chat.messages')
async def messages(partner_id: int = Path(gt=0), before_id: int | None = Query(default=None, gt=0),
                   limit: int = Query(default=50, ge=1, le=100), user: dict = Depends(get_current_user)):
    return await run('chat.messages', HistoryDTO(me_id=user['user_id'], partner_id=partner_id,
                                                 before_id=before_id, limit=limit))


@router.post('/dialogs/{partner_id}/messages', response_model=SendResult, status_code=201)
@external_scenario('chat.send', core='chat.send')
async def send(body: TextBody, partner_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    result = await run('chat.send', SendDTO(me_id=user['user_id'], partner_id=partner_id, text=body.text))
    await deliver(result)
    return result


@router.post('/dialogs/{partner_id}/read', response_model=ReadResult)
@external_scenario('chat.read', core='chat.read')
async def read(partner_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    result = await run('chat.read', DialogDTO(me_id=user['user_id'], partner_id=partner_id))
    notify_read(user['user_id'], result)
    return result


@router.get('/board/{board_id}/dialogs', response_model=DialogList)
@external_scenario('chat.board_dialogs', core='chat.dialogs')
async def board_dialogs(board_id: str = Path(max_length=40), user: dict = Depends(get_current_user)):
    """Диалоги с теми, кто сейчас на этой доске и связан со мной (панель чата доски)."""
    me = user['user_id']
    room = board_hub.rooms.get(board_id)
    present = {p.user_id for p in room.peers.values()} if room else set()
    if me not in present:
        return DialogList(items=[])
    result = await run('chat.dialogs', MeDTO(me_id=me))
    items = [d for d in result.items if d.partner_id in present and d.can_write]
    return DialogList(items=items, unread_total=sum(d.unread for d in items))


# ---------- WebSocket ----------

async def _sender(conn: ChatConn):
    try:
        while True:
            await conn.ws.send_text(await conn.queue.get())
            if conn.closed:
                break
    except Exception:
        pass
    conn.closed = True
    try:
        await conn.ws.close(code=1011)
    except Exception:
        pass


@router.websocket('/ws')
@external_scenario('chat.live', core='chat.send')
async def chat_socket(ws: WebSocket):
    """Первое сообщение — {"t":"hello","token":...}; дальше send / read / ping."""
    if not origin_allowed(ws):
        await ws.close(code=CLOSE_FORBIDDEN)
        return
    await ws.accept()
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=10))
        token = str(hello.get('token') or '')
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError, AttributeError):
        await ws.close(code=CLOSE_POLICY, reason='hello expected')
        return
    policy = ws.app.state.access_policy
    try:
        principal = authenticate('Bearer ' + token, policy)
    except CoreError:
        principal = None
    if principal is None or 'chat.live' not in policy.get(principal['role'], ()):
        await ws.close(code=CLOSE_FORBIDDEN, reason='login required')
        return
    me = principal['user_id']
    conn = ChatConn(ws=ws, user_id=me)
    chat_hub.add(conn)
    sender = asyncio.create_task(_sender(conn))
    limiter = RateLimiter(2, 10)
    conn.send({'t': 'ready'})
    try:
        while not conn.closed:
            text = await ws.receive_text()
            if len(text) > TEXT_MAX * 4:
                await ws.close(code=1009, reason='message too big')
                break
            try:
                msg = json.loads(text)
            except ValueError:
                continue
            kind = msg.get('t') if isinstance(msg, dict) else None
            if kind == 'ping':
                conn.send({'t': 'pong'})
            elif kind == 'send':
                if not limiter.allow():
                    conn.send({'t': 'error', 'cid': msg.get('cid'), 'message': 'Слишком часто — подождите секунду'})
                    continue
                try:
                    result = await run('chat.send', SendDTO(me_id=me, partner_id=int(msg.get('to') or 0),
                                                            text=str(msg.get('text') or '')))
                except (ValidationError, CoreError, ValueError, TypeError) as exc:
                    conn.send({'t': 'error', 'cid': msg.get('cid'), 'message': _message(exc)})
                    continue
                conn.send({'t': 'sent', 'cid': msg.get('cid'), 'id': result.message.id})
                await deliver(result)
            elif kind == 'read':
                try:
                    result = await run('chat.read', DialogDTO(me_id=me, partner_id=int(msg.get('with') or 0)))
                except (ValidationError, CoreError, ValueError, TypeError):
                    continue
                notify_read(me, result)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception('chat socket failed')
    finally:
        conn.closed = True
        chat_hub.remove(conn)
        sender.cancel()


def _message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return 'Сообщение пустое или слишком длинное'
    return str(exc) or 'Не удалось отправить сообщение'
