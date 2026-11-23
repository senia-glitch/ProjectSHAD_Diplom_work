from typing import Optional, Literal
from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.db_errors import is_unique_violation
from app.utils.validation import EMAIL_PATTERN, USERNAME_PATTERN
from core.dto import BaseDTO


class AdminListUsersDTO(BaseDTO):
    role: Optional[str] = None


class UserItem(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None
    role_name: str


class AdminListUsersResponse(BaseModel):
    users: list[UserItem]


class AdminGetUserByIdDTO(BaseDTO):
    target_user_id: int


class AdminGetUserByIdResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None
    role_name: str
    profile: dict | None = None


class AdminUpdateUserDTO(BaseDTO):
    # target_user_id в теле не обязателен: роут обязан подставить его
    # из пути, единый источник истины — {user_id} в URL.
    target_user_id: int | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255, pattern=EMAIL_PATTERN)
    gender: Literal["male", "female", "other"] | None = None
    additional_info: str | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    personal_number: str | None = Field(default=None, min_length=1, max_length=50)


class AdminUpdateUserResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str
    personal_number: str
    gender: str | None
    additional_info: str | None
    role_name: str


def _actor(dto: BaseDTO):
    token = extract_token_info(dto.access_token)
    return token


@register_scenario("admin_list_users", dto=AdminListUsersDTO, response=AdminListUsersResponse)
@tracked_scenario("admin_list_users")
class AdminListUsersScenario(BaseScenario):
    async def execute(self, dto: AdminListUsersDTO) -> AdminListUsersResponse:
        _actor(dto)

        if dto.role:
            rows = await self._db.query(
                """SELECT u.id AS user_id, u.username, u.full_name, u.email,
                          u.personal_number, u.gender, u.additional_info,
                          r.name AS role_name
                   FROM "users" u
                   JOIN "roles" r ON r.id = u.role_id
                   WHERE r.name = :role
                   ORDER BY u.id LIMIT :lim OFFSET :off""",
                {"role": dto.role, "lim": dto.limit, "off": dto.offset},
            )
        else:
            rows = await self._db.query(
                """SELECT u.id AS user_id, u.username, u.full_name, u.email,
                          u.personal_number, u.gender, u.additional_info,
                          r.name AS role_name
                   FROM "users" u
                   JOIN "roles" r ON r.id = u.role_id
                   ORDER BY u.id LIMIT :lim OFFSET :off""",
                {"lim": dto.limit, "off": dto.offset},
            )

        return AdminListUsersResponse(
            users=[UserItem(**r) for r in rows]
        )


@register_scenario("admin_get_user_by_id", dto=AdminGetUserByIdDTO, response=AdminGetUserByIdResponse)
@tracked_scenario("admin_get_user_by_id")
class AdminGetUserByIdScenario(BaseScenario):
    async def execute(self, dto: AdminGetUserByIdDTO) -> AdminGetUserByIdResponse:
        _actor(dto)

        user_rows = await self._db.query(
            """SELECT u.id AS user_id, u.username, u.full_name, u.email,
                      u.personal_number, u.gender, u.additional_info,
                      r.name AS role_name
               FROM "users" u
               JOIN "roles" r ON r.id = u.role_id
               WHERE u.id = :uid""",
            {"uid": dto.target_user_id},
        )

        if not user_rows:
            raise NotFoundError("User not found")

        user = dict(user_rows[0])
        role_name = user["role_name"]

        profile = None
        if role_name == "student":
            profile_rows = await self._db.query(
                'SELECT * FROM "students" WHERE user_id = :uid',
                {"uid": dto.target_user_id},
            )
            if profile_rows:
                profile = dict(profile_rows[0])
        elif role_name == "tutor":
            profile_rows = await self._db.query(
                'SELECT * FROM "tutors" WHERE user_id = :uid',
                {"uid": dto.target_user_id},
            )
            if profile_rows:
                profile = dict(profile_rows[0])
        elif role_name == "admin":
            profile_rows = await self._db.query(
                'SELECT * FROM "admins" WHERE user_id = :uid',
                {"uid": dto.target_user_id},
            )
            if profile_rows:
                profile = dict(profile_rows[0])

        user["profile"] = profile
        return AdminGetUserByIdResponse(**user)


@register_scenario("admin_update_user", dto=AdminUpdateUserDTO, response=AdminUpdateUserResponse)
@tracked_scenario("admin_update_user")
class AdminUpdateUserScenario(BaseScenario):
    async def execute(self, dto: AdminUpdateUserDTO) -> AdminUpdateUserResponse:
        _actor(dto)
        if dto.target_user_id is None:
            raise ValidationError("target_user_id is required")

        existing = await self._db.query(
            'SELECT id FROM "users" WHERE id = :uid',
            {"uid": dto.target_user_id},
        )
        if not existing:
            raise NotFoundError("User not found")

        update_fields = {}
        if dto.full_name is not None:
            update_fields["full_name"] = dto.full_name
        if dto.email is not None:
            update_fields["email"] = dto.email
        if dto.gender is not None:
            update_fields["gender"] = dto.gender
        if dto.additional_info is not None:
            update_fields["additional_info"] = dto.additional_info
        if dto.username is not None:
            update_fields["username"] = dto.username
        if dto.personal_number is not None:
            update_fields["personal_number"] = dto.personal_number

        if not update_fields:
            raise ValidationError("No fields to update")

        try:
            await self._db.update("users", dto.target_user_id, update_fields)
        except Exception as e:
            if is_unique_violation(e):
                raise ConflictError("Username, email or personal number already in use")
            raise

        updated_rows = await self._db.query(
            """SELECT u.id AS user_id, u.username, u.full_name, u.email,
                      u.personal_number, u.gender, u.additional_info,
                      r.name AS role_name
               FROM "users" u
               JOIN "roles" r ON r.id = u.role_id
               WHERE u.id = :uid""",
            {"uid": dto.target_user_id},
        )

        return AdminUpdateUserResponse(**updated_rows[0])
