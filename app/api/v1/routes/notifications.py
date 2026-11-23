from fastapi import APIRouter, Depends, Header, Query
from core import run
from core.dto import BaseDTO
from app.api.v1.dependencies import get_current_user, require_auth
from app.scenarios.notifications.my import NotificationsMarkReadDTO

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
@require_auth()
async def list_notifications(
    limit: int = Query(default=30, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = BaseDTO(access_token=authorization.split(" ")[1], limit=limit, offset=offset)
    return await run("notifications_list", dto)


@router.get("/unread-count")
@require_auth()
async def unread_count(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = BaseDTO(access_token=authorization.split(" ")[1])
    return await run("notifications_unread_count", dto)


@router.post("/{notification_id}/read")
@require_auth()
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


@router.post("/read-all")
@require_auth()
async def read_all(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = BaseDTO(access_token=authorization.split(" ")[1])
    return await run("notifications_read_all", dto)