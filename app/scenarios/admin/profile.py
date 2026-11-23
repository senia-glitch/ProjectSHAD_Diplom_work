from pydantic import BaseModel
from core import BaseScenario, NotFoundError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO


class AdminGetMyProfileDTO(BaseDTO):
    pass


class AdminGetMyProfileResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None


@register_scenario("admin_get_my_profile", dto=AdminGetMyProfileDTO, response=AdminGetMyProfileResponse)
@tracked_scenario("admin_get_my_profile")
class AdminGetMyProfileScenario(BaseScenario):
    async def execute(self, dto: AdminGetMyProfileDTO) -> AdminGetMyProfileResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            'SELECT * FROM "users" WHERE id = :uid',
            {"uid": token.user_id},
        )

        if not rows:
            raise NotFoundError("Admin profile not found")

        u = rows[0]
        return AdminGetMyProfileResponse(
            user_id=u["id"],
            username=u["username"],
            full_name=u["full_name"],
            email=u["email"],
            personal_number=u["personal_number"],
            gender=u.get("gender"),
            additional_info=u.get("additional_info"),
        )
