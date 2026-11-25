from pydantic import BaseModel
from core import BaseScenario, NotFoundError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO
from app.utils.notifications import user_offset


class GetMeDTO(BaseDTO):
    pass


class GetMeResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str
    role: str
    personal_number: str
    gender: str | None
    additional_info: str | None
    avatar_url: str | None = None
    # Личный пояс (часы от UTC): клиент показывает время в нём.
    timezone_offset: int = 0


@register_scenario("get_me", dto=GetMeDTO, response=GetMeResponse)
@tracked_scenario("get_me")
class GetMeScenario(BaseScenario):
    async def execute(self, dto: GetMeDTO) -> GetMeResponse:
        token = extract_token_info(dto.access_token)
        user = await self._db.read("users", token.user_id)
        if not user:
            raise NotFoundError("User not found")

        role_rows = await self._db.query(
            'SELECT name FROM "roles" WHERE id = :role_id',
            {"role_id": user["role_id"]},
        )
        role_name = role_rows[0]["name"] if role_rows else "unknown"

        return GetMeResponse(
            user_id=user["id"],
            username=user["username"],
            full_name=user["full_name"],
            email=user["email"],
            role=role_name,
            personal_number=user["personal_number"],
            gender=user.get("gender"),
            additional_info=user.get("additional_info"),
            avatar_url=user.get("avatar_url"),
            timezone_offset=await user_offset(self._db, user["id"]),
        )
