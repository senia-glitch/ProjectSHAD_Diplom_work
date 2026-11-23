from pydantic import BaseModel
from core import BaseScenario, NotFoundError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO


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
        )
