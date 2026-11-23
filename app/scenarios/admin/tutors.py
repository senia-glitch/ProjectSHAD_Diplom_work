from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO


class AdminListTutorsDTO(BaseDTO):
    pass


class TutorItem(BaseModel):
    tutor_id: int
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None


class AdminListTutorsResponse(BaseModel):
    tutors: list[TutorItem]


@register_scenario("admin_list_tutors", dto=AdminListTutorsDTO, response=AdminListTutorsResponse)
@tracked_scenario("admin_list_tutors")
class AdminListTutorsScenario(BaseScenario):
    async def execute(self, dto: AdminListTutorsDTO) -> AdminListTutorsResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            """SELECT t.id AS tutor_id, t.user_id,
                      u.username, u.full_name, u.email,
                      u.personal_number, u.gender, u.additional_info
               FROM "tutors" t
               JOIN "users" u ON u.id = t.user_id
               ORDER BY t.id
               LIMIT :lim OFFSET :off""",
            {"lim": dto.limit, "off": dto.offset},
        )

        return AdminListTutorsResponse(
            tutors=[TutorItem(**r) for r in rows]
        )
