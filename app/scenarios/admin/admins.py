from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.core.exceptions import ForbiddenError
from core.dto import BaseDTO


class AdminListAdminsDTO(BaseDTO):
    pass


class AdminItem(BaseModel):
    admin_id: int
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None


class AdminListAdminsResponse(BaseModel):
    admins: list[AdminItem]


@register_scenario("admin_list_admins")
@tracked_scenario("admin_list_admins")
class AdminListAdminsScenario(BaseScenario):
    async def execute(self, dto: AdminListAdminsDTO) -> AdminListAdminsResponse:
        token = extract_token_info(dto.access_token)
        if token.role != "admin":
            raise ForbiddenError("Only admins can access this endpoint")

        rows = await self._db.query(
            """SELECT a.id AS admin_id, a.user_id,
                      u.username, u.full_name, u.email,
                      u.personal_number, u.gender, u.additional_info
               FROM "admins" a
               JOIN "users" u ON u.id = a.user_id
               ORDER BY a.id
               LIMIT :lim OFFSET :off""",
            {"lim": dto.limit, "off": dto.offset},
        )

        return AdminListAdminsResponse(
            admins=[AdminItem(**r) for r in rows]
        )
