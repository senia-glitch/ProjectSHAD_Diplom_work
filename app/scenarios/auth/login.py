from pydantic import BaseModel, Field
from core import BaseScenario, ValidationError, register_scenario, tracked_scenario
from core.utils.security import verify_password, create_access_token, create_refresh_token
from app.utils.validation import PasswordInputStr
from app.core.exceptions import ForbiddenError
from app.utils.tokens import create_refresh_store, hash_refresh_token

# Фиктивный bcrypt-хеш для выравнивания времени ответа: не даёт отличать
# несуществующего пользователя от неверного пароля по времени выполнения.
_DUMMY_PASSWORD_HASH = "$2b$12$0sVjlSlLw9GjGneAhFHpmeR0vn7tEhJDPnp0Oz.KSD3XzG4NTDqBW"


class LoginDTO(BaseModel):
    username: str = Field(..., max_length=50)
    password: PasswordInputStr


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    role: str


@register_scenario("login", dto=LoginDTO, response=LoginResponse)
@tracked_scenario("login")
class LoginScenario(BaseScenario):
    async def execute(self, dto: LoginDTO) -> LoginResponse:
        rows = await self._db.query(
            'SELECT * FROM "users" WHERE username = :username',
            {"username": dto.username},
        )
        user = rows[0] if rows else None
        if not user:
            # Выполняем фиктивную проверку, чтобы время ответа не выдавало
            # существование пользователя (защита от timing-энумерации).
            await verify_password(dto.password, _DUMMY_PASSWORD_HASH)
            raise ValidationError("Invalid username or password")

        password_valid = await verify_password(dto.password, user["password_hash"])
        if not password_valid:
            raise ValidationError("Invalid username or password")
        # Администратор входит только по ключу (/admin/login); по паролю — как неверные данные,
        # чтобы форма входа не подтверждала существование учётной записи владельца.
        admins = await self._db.query('SELECT id FROM "admins" WHERE user_id = :uid', {"uid": user["id"]})
        if admins:
            raise ValidationError("Invalid username or password")
        if user.get("blocked_at"):
            raise ForbiddenError("Account is blocked")

        role_rows = await self._db.query(
            'SELECT * FROM "roles" WHERE id = :role_id',
            {"role_id": user["role_id"]},
        )
        role = role_rows[0] if role_rows else None
        if not role:
            raise ValidationError("Role not found")

        access_token = create_access_token(user["id"], role["name"])
        refresh_token = create_refresh_token(user["id"])
        await self._db.update("users", user["id"], {
            "refresh_token": create_refresh_store(user.get("refresh_token"), hash_refresh_token(refresh_token)),
        })

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user["id"],
            role=role["name"],
        )
