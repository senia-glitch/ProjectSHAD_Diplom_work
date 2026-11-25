from typing import Literal, Annotated

from pydantic import BaseModel, Field, BeforeValidator
from core import BaseScenario, NotFoundError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.db_errors import is_unique_violation
from app.utils.validation import EMAIL_PATTERN
from core.dto import BaseDTO


def _avatar_url(value):
    """Фото профиля: пустая строка убирает фото, иначе только ссылка http(s) без пробелов."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return ""
    if not text.lower().startswith(("https://", "http://")) or any(c.isspace() for c in text):
        raise ValueError("avatar_url must be an http(s) link")
    return text


def _require_visible_name(value):
    """full_name не может быть пустой строкой или одними пробелами."""
    if value is None:
        return None
    if not str(value).strip():
        raise ValueError("full_name must not be empty")
    return value


class UpdateMeDTO(BaseDTO):
    full_name: Annotated[str | None, BeforeValidator(_require_visible_name)] = Field(
        default=None, max_length=255
    )
    email: str | None = Field(default=None, max_length=255, pattern=EMAIL_PATTERN)
    gender: Literal["male", "female", "other"] | None = None
    additional_info: str | None = None
    avatar_url: Annotated[str | None, BeforeValidator(_avatar_url)] = Field(default=None, max_length=500)


class UpdateMeResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    gender: str | None
    additional_info: str | None
    avatar_url: str | None = None


@register_scenario("update_me", dto=UpdateMeDTO, response=UpdateMeResponse)
@tracked_scenario("update_me")
class UpdateMeScenario(BaseScenario):
    async def execute(self, dto: UpdateMeDTO) -> UpdateMeResponse:
        token = extract_token_info(dto.access_token)
        user = await self._db.read("users", token.user_id)
        if not user:
            raise NotFoundError("User not found")

        update_data = {}
        if dto.full_name is not None:
            update_data["full_name"] = dto.full_name
        if dto.email is not None:
            update_data["email"] = dto.email
        if dto.gender is not None:
            update_data["gender"] = dto.gender
        if dto.additional_info is not None:
            update_data["additional_info"] = dto.additional_info
        if dto.avatar_url is not None:
            update_data["avatar_url"] = dto.avatar_url or None

        if update_data:
            try:
                await self._db.update("users", token.user_id, update_data)
            except Exception as e:
                if is_unique_violation(e):
                    raise ConflictError("Email already registered")
                raise

        updated = await self._db.read("users", token.user_id)
        return UpdateMeResponse(
            user_id=updated["id"],
            full_name=updated["full_name"],
            email=updated["email"],
            gender=updated.get("gender"),
            additional_info=updated.get("additional_info"),
            avatar_url=updated.get("avatar_url"),
        )
