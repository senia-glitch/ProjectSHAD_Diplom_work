from core import run
from core.dto import BaseDTO
from fastapi import APIRouter, Depends, Header, Query
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.notifications.my import (
    NotificationsListResponse,
    NotificationsMarkReadDTO,
    NotificationsMarkReadResponse,
    NotificationsReadAllResponse,
    NotificationsUnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsListResponse)
@external_scenario("notifications.list_notifications", core="notifications_list")
async def list_notifications(
    limit: int = Query(default=30, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = BaseDTO(access_token=authorization.split(" ")[1], limit=limit, offset=offset)
    return await run("notifications_list", dto)


@router.get("/unread-count", response_model=NotificationsUnreadCountResponse)
@external_scenario("notifications.unread_count", core="notifications_unread_count")
async def unread_count(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = BaseDTO(access_token=authorization.split(" ")[1])
    return await run("notifications_unread_count", dto)


@router.post("/{notification_id}/read", response_model=NotificationsMarkReadResponse)
@external_scenario("notifications.mark_read", core="notifications_mark_read")
async def mark_read(
    notification_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = NotificationsMarkReadDTO(
        access_token=authorization.split(" ")[1],
        notification_id=notification_id,
    )
    return await run("notifications_mark_read", dto)


@router.post("/read-all", response_model=NotificationsReadAllResponse)
@external_scenario("notifications.read_all", core="notifications_read_all")
async def read_all(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = BaseDTO(access_token=authorization.split(" ")[1])
    return await run("notifications_read_all", dto)
