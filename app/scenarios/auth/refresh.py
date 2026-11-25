from pydantic import BaseModel
from core import BaseScenario, ValidationError, register_scenario, tracked_scenario
from core.utils.security import decode_token, create_access_token, create_refresh_token
from app.utils.tokens import (
    auth_user_lock,
    format_refresh_hashes,
    hash_refresh_token,
    parse_refresh_hashes,
    rotate_refresh_store,
)


class RefreshDTO(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


@register_scenario("refresh", dto=RefreshDTO, response=RefreshResponse)
@tracked_scenario("refresh")
class RefreshScenario(BaseScenario):
    async def execute(self, dto: RefreshDTO) -> RefreshResponse:
        try:
            payload = decode_token(dto.refresh_token)
        except Exception:
            raise ValidationError("Invalid token")

        if payload.get("type") != "refresh":
            raise ValidationError("Invalid token type")

        user_id = int(payload["sub"])
        # Ротация списка сессий сериализована: read-modify-write не должен
        # потерять сессию, открытую параллельным refresh того же токена.
        async with (await auth_user_lock(user_id)):
            user = await self._db.read("users", user_id)
            if not user:
                raise ValidationError("User not found")
            if user.get("blocked_at"):
                raise ValidationError("Account is blocked")

            stored_token = user.get("refresh_token")
            old_hash = hash_refresh_token(dto.refresh_token)
            hashes = parse_refresh_hashes(stored_token)
            if stored_token is None or old_hash not in hashes:
                raise ValidationError("Refresh token revoked")

            role_rows = await self._db.query(
                'SELECT * FROM "roles" WHERE id = :role_id',
                {"role_id": user["role_id"]},
            )
            role = role_rows[0] if role_rows else None
            if not role:
                raise ValidationError("Role not found")

            new_access = create_access_token(user_id, role["name"])
            new_refresh = create_refresh_token(user_id)
            await self._db.update(
                "users",
                user_id,
                {"refresh_token": format_refresh_hashes(
                    rotate_refresh_store(stored_token, old_hash, hash_refresh_token(new_refresh))
                )},
            )

            return RefreshResponse(access_token=new_access, refresh_token=new_refresh)
