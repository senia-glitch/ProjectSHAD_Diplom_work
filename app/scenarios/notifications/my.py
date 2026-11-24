from app.utils.clock import utc_now, to_utc_naive
import datetime

from pydantic import BaseModel
from core import BaseScenario, NotFoundError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.json_codec import parse_rows
from core.dto import BaseDTO


class NotificationItem(BaseModel):
    id: int
    type: str
    text: str
    read: bool
    created_at: str


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationItem]
    unread_count: int


class NotificationsUnreadCountResponse(BaseModel):
    count: int


class NotificationsMarkReadDTO(BaseDTO):
    notification_id: int


class NotificationsMarkReadResponse(BaseModel):
    ok: bool


class NotificationsReadAllResponse(BaseModel):
    updated: int


@register_scenario("notifications_list", dto=BaseDTO, response=NotificationsListResponse)
@tracked_scenario("notifications_list")
class NotificationsListScenario(BaseScenario):
    async def execute(self, dto: BaseDTO) -> NotificationsListResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            'SELECT * FROM "notifications" WHERE user_id = :uid ORDER BY id DESC LIMIT :lim OFFSET :off',
            {"uid": token.user_id, "lim": dto.limit, "off": dto.offset},
        )
        count_rows = await self._db.query(
            'SELECT COUNT(*) AS cnt FROM "notifications" WHERE user_id = :uid AND read_at IS NULL',
            {"uid": token.user_id},
        )
        unread = count_rows[0]["cnt"] if count_rows else 0

        items = []
        for n in parse_rows("notifications", rows):
            payload = n.get("payload") or {}
            items.append(NotificationItem(
                id=n["id"],
                type=n["type"],
                text=payload.get("text") or "",
                read=n.get("read_at") is not None,
                created_at=str(n["created_at"]),
            ))

        return NotificationsListResponse(notifications=items, unread_count=unread)


@register_scenario("notifications_unread_count", dto=BaseDTO, response=NotificationsUnreadCountResponse)
@tracked_scenario("notifications_unread_count")
class NotificationsUnreadCountScenario(BaseScenario):
    async def execute(self, dto: BaseDTO) -> NotificationsUnreadCountResponse:
        token = extract_token_info(dto.access_token)

        count_rows = await self._db.query(
            'SELECT COUNT(*) AS cnt FROM "notifications" WHERE user_id = :uid AND read_at IS NULL',
            {"uid": token.user_id},
        )
        return NotificationsUnreadCountResponse(count=count_rows[0]["cnt"] if count_rows else 0)


@register_scenario("notifications_mark_read", dto=NotificationsMarkReadDTO, response=NotificationsMarkReadResponse)
@tracked_scenario("notifications_mark_read")
class NotificationsMarkReadScenario(BaseScenario):
    async def execute(self, dto: NotificationsMarkReadDTO) -> NotificationsMarkReadResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            'SELECT * FROM "notifications" WHERE id = :nid',
            {"nid": dto.notification_id},
        )
        if not rows or rows[0]["user_id"] != token.user_id:
            raise NotFoundError("Notification not found")

        if rows[0].get("read_at") is None:
            await self._db.update("notifications", dto.notification_id, {"read_at": utc_now()})

        return NotificationsMarkReadResponse(ok=True)


@register_scenario("notifications_read_all", dto=BaseDTO, response=NotificationsReadAllResponse)
@tracked_scenario("notifications_read_all")
class NotificationsReadAllScenario(BaseScenario):
    async def execute(self, dto: BaseDTO) -> NotificationsReadAllResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            'SELECT id FROM "notifications" WHERE user_id = :uid AND read_at IS NULL ORDER BY id',
            {"uid": token.user_id},
        )
        now = utc_now()
        for row in rows:
            await self._db.update("notifications", row["id"], {"read_at": now})

        return NotificationsReadAllResponse(updated=len(rows))
