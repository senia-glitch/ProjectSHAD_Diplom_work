from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario


class InitRolesResponse(BaseModel):
    created: list[str]
    already_exist: list[str]


@register_scenario("init_roles", response=InitRolesResponse)
@tracked_scenario("init_roles")
class InitRolesScenario(BaseScenario):
    async def execute(self, dto=None) -> InitRolesResponse:
        roles = ["student", "tutor", "admin"]
        created = []
        already_exist = []

        for role_name in roles:
            rows = await self._db.query(
                'SELECT id FROM "roles" WHERE name = :name',
                {"name": role_name},
            )
            if rows:
                already_exist.append(role_name)
            else:
                await self._db.create("roles", {"name": role_name})
                created.append(role_name)

        return InitRolesResponse(created=created, already_exist=already_exist)
