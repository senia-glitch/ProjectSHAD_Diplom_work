from typing import Literal, Annotated

from pydantic import BaseModel, Field, BeforeValidator
from core import BaseScenario, NotFoundError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.utils.db_errors import is_unique_violation
from app.utils.validation import EMAIL_PATTERN
from core.dto import BaseDTO


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


class UpdateMeResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    gender: str | None
    additional_info: str | None


@register_scenario("update_me")
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
        )
