from pydantic import BaseModel, Field
from core import BaseScenario, ValidationError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import hash_password, create_access_token, create_refresh_token
from app.utils.tokens import format_refresh_hashes, hash_refresh_token
from app.utils.db_errors import is_unique_violation
from app.utils.validation import PasswordStr
import secrets
import string


def _generate_personal_number() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "IND-" + "".join(secrets.choice(alphabet) for _ in range(8))


class RegisterUserDTO(BaseModel):
    # Открытая регистрация: только student/tutor. Создание admin —
    # только через сид/админ-панель, иначе privilege escalation.
    role: str = Field(..., description="student, tutor")
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: PasswordStr
    full_name: str = Field(..., min_length=1, max_length=255)
    # Без EmailStr: email-validator не входит в зависимости проекта.
    # Простая проверка формата вместо полной RFC-валидации.
    email: str = Field(..., min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterUserResponse(BaseModel):
    user_id: int
    role: str
    profile_id: int
    settings_id: int | None = None
    access_token: str
    refresh_token: str


@register_scenario("register")
@tracked_scenario("register")
class RegisterUserScenario(BaseScenario):
    async def execute(self, dto: RegisterUserDTO) -> RegisterUserResponse:
        if dto.role not in ("student", "tutor"):
            raise ValidationError(f"Invalid role: {dto.role}. Open registration allows only 'student' or 'tutor'")

        existing = await self._db.query(
            'SELECT id FROM "users" WHERE username = :username',
            {"username": dto.username},
        )
        if existing:
            raise ConflictError("Username or email already registered")

        existing_email = await self._db.query(
            'SELECT id FROM "users" WHERE email = :email',
            {"email": dto.email},
        )
        if existing_email:
            raise ConflictError("Username or email already registered")

        personal_number = _generate_personal_number()
        for _ in range(10):
            existing_pn = await self._db.query(
                'SELECT id FROM "users" WHERE personal_number = :pn',
                {"pn": personal_number},
            )
            if not existing_pn:
                break
            personal_number = _generate_personal_number()
        else:
            raise ValidationError("Failed to generate unique personal number")

        role_rows = await self._db.query(
            'SELECT id FROM "roles" WHERE name = :name',
            {"name": dto.role},
        )
        role = role_rows[0] if role_rows else None
        if not role:
            raise ValidationError(f"Role '{dto.role}' not found")

        password_hash = await hash_password(dto.password)

        try:
            user = await self._db.create("users", {
                "role_id": role["id"],
                "username": dto.username,
                "personal_number": personal_number,
                "password_hash": password_hash,
                "full_name": dto.full_name,
                "email": dto.email,
            })
        except Exception as e:
            if is_unique_violation(e):
                raise ConflictError("Username, email or personal number already registered")
            raise

        settings_id = None
        created_profile: dict | None = None
        try:
            if dto.role == "student":
                profile = await self._db.create("students", {"user_id": user["id"]})
                created_profile = profile
                settings = await self._db.create("student_settings", {"student_id": profile["id"]})
                settings_id = settings["id"]
            else:
                profile = await self._db.create("tutors", {"user_id": user["id"]})
                created_profile = profile
                settings = await self._db.create("tutor_settings", {"tutor_id": profile["id"]})
                settings_id = settings["id"]
        except Exception:
            # Компенсация: не оставляем сироты в users. Профиль мог уже
            # создаться (чистый remove users упрётся в FK), поэтому
            # откат в обратном порядке: настройки → профиль → users.
            profile_id = created_profile["id"] if created_profile else None
            if profile_id:
                if dto.role == "student":
                    settings_table, profile_table, column = "student_settings", "students", "student_id"
                else:
                    settings_table, profile_table, column = "tutor_settings", "tutors", "tutor_id"
                try:
                    await self._db.query(
                        f'DELETE FROM "{settings_table}" WHERE {column} = :pid',
                        {"pid": profile_id},
                        channel="write",
                    )
                except Exception:
                    pass
                try:
                    await self._db.query(
                        f'DELETE FROM "{profile_table}" WHERE id = :pid',
                        {"pid": profile_id},
                        channel="write",
                    )
                except Exception:
                    pass
            try:
                await self._db.delete("users", user["id"])
            except Exception:
                pass
            raise

        access_token = create_access_token(user["id"], dto.role)
        refresh_token = create_refresh_token(user["id"])
        await self._db.update("users", user["id"], {
            "refresh_token": format_refresh_hashes([hash_refresh_token(refresh_token)]),
        })

        return RegisterUserResponse(
            user_id=user["id"],
            role=dto.role,
            profile_id=profile["id"],
            settings_id=settings_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
