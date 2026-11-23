from pydantic import BaseModel, Field
from core import BaseScenario, NotFoundError, ValidationError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info, verify_password, hash_password
from app.utils.validation import PasswordStr, PasswordInputStr
from core.dto import BaseDTO


class ChangePasswordDTO(BaseDTO):
    old_password: PasswordInputStr = Field(...)
    new_password: PasswordStr


class ChangePasswordResponse(BaseModel):
    ok: bool


@register_scenario("change_password", dto=ChangePasswordDTO, response=ChangePasswordResponse)
@tracked_scenario("change_password")
class ChangePasswordScenario(BaseScenario):
    async def execute(self, dto: ChangePasswordDTO) -> ChangePasswordResponse:
        token = extract_token_info(dto.access_token)
        user = await self._db.read("users", token.user_id)
        if not user:
            raise NotFoundError("User not found")

        valid = await verify_password(dto.old_password, user["password_hash"])
        if not valid:
            raise ValidationError("Invalid current password")

        new_hash = await hash_password(dto.new_password)
        # Инвалидируем все refresh-сессии: иначе старый refresh живёт 30 дней
        # после смены пароля. Пользователю нужно залогиниться заново.
        await self._db.update("users", token.user_id, {"password_hash": new_hash, "refresh_token": None})

        return ChangePasswordResponse(ok=True)
