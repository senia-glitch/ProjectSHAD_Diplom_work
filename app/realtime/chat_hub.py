"""Доставка личных сообщений в реальном времени.

Один процесс приложения (FAT_WORKERS=1): соединения пользователей хранятся в памяти.
У пользователя может быть несколько открытых вкладок — событие получают все.
"""
import asyncio
import json
from dataclasses import dataclass, field

from fastapi import WebSocket

SEND_QUEUE = 200


@dataclass(eq=False)
class ChatConn:
    ws: WebSocket
    user_id: int
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=SEND_QUEUE))
    closed: bool = False

    def send(self, message: dict):
        if self.closed:
            return
        try:
            self.queue.put_nowait(json.dumps(message, ensure_ascii=False, default=str))
        except asyncio.QueueFull:
            self.closed = True  # клиент не читает: соединение закроет отправитель


class ChatHub:
    def __init__(self):
        self.users: dict[int, set[ChatConn]] = {}

    def add(self, conn: ChatConn):
        self.users.setdefault(conn.user_id, set()).add(conn)

    def remove(self, conn: ChatConn):
        conns = self.users.get(conn.user_id)
        if conns:
            conns.discard(conn)
            if not conns:
                self.users.pop(conn.user_id, None)

    def push(self, user_id: int, message: dict):
        for conn in list(self.users.get(user_id, ())):
            conn.send(message)

    def online(self, user_id: int) -> bool:
        return bool(self.users.get(user_id))


chat_hub = ChatHub()
