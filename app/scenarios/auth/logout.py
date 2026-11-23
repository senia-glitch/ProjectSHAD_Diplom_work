from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario
from core.utils.security import decode_token
from app.utils.tokens import auth_user_lock, hash_refresh_token, revoke_refresh_session


class LogoutDTO(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    ok: bool


@register_scenario("logout")
@tracked_scenario("logout")
class LogoutScenario(BaseScenario):
    async def execute(self, dto: LogoutDTO) -> LogoutResponse:
        try:
            payload = decode_token(dto.refresh_token)
        except Exception:
            return LogoutResponse(ok=True)

        if payload.get("type") != "refresh":
            return LogoutResponse(ok=True)

        user_id = int(payload["sub"])
        # Убираем из списка сессий только ТОКЕН ЭТОЙ вкладки: другие
        # устройства/вкладки с их refresh-токенами остаются рабочими.
        async with (await auth_user_lock(user_id)):
            user = await self._db.read("users", user_id)
            if user:
                await self._db.update("users", user_id, {
                    "refresh_token": revoke_refresh_session(
                        user.get("refresh_token"), hash_refresh_token(dto.refresh_token)
                    ),
                })

        return LogoutResponse(ok=True)
