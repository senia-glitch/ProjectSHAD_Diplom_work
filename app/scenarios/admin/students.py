from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO


class AdminListStudentsDTO(BaseDTO):
    pass


class StudentItem(BaseModel):
    student_id: int
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None


class AdminListStudentsResponse(BaseModel):
    students: list[StudentItem]


@register_scenario("admin_list_students", dto=AdminListStudentsDTO, response=AdminListStudentsResponse)
@tracked_scenario("admin_list_students")
class AdminListStudentsScenario(BaseScenario):
    async def execute(self, dto: AdminListStudentsDTO) -> AdminListStudentsResponse:
        token = extract_token_info(dto.access_token)

        rows = await self._db.query(
            """SELECT s.id AS student_id, s.user_id,
                      u.username, u.full_name, u.email,
                      u.personal_number, u.gender, u.additional_info
               FROM "students" s
               JOIN "users" u ON u.id = s.user_id
               ORDER BY s.id
               LIMIT :lim OFFSET :off""",
            {"lim": dto.limit, "off": dto.offset},
        )

        return AdminListStudentsResponse(
            students=[StudentItem(**r) for r in rows]
        )
