from pydantic import BaseModel
from core import BaseScenario, NotFoundError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from core.dto import BaseDTO


class DeleteMeDTO(BaseDTO):
    pass


class DeleteMeResponse(BaseModel):
    ok: bool


@register_scenario("delete_me", dto=DeleteMeDTO, response=DeleteMeResponse)
@tracked_scenario("delete_me")
class DeleteMeScenario(BaseScenario):
    async def execute(self, dto: DeleteMeDTO) -> DeleteMeResponse:
        token = extract_token_info(dto.access_token)
        user = await self._db.read("users", token.user_id)
        if not user:
            raise NotFoundError("User not found")

        role_rows = await self._db.query(
            'SELECT name FROM "roles" WHERE id = :role_id',
            {"role_id": user["role_id"]},
        )
        role_name = role_rows[0]["name"] if role_rows else None

        if role_name == "student":
            profiles = await self._db.query(
                'SELECT id FROM "students" WHERE user_id = :uid',
                {"uid": token.user_id},
            )
            if profiles:
                profile_id = profiles[0]["id"]
                await self._db.query(
                    'DELETE FROM "lesson_participants" WHERE student_id = :sid',
                    {"sid": profile_id},
                    channel="write",
                )
                await self._db.query(
                    'DELETE FROM "configurations" WHERE student_id = :sid',
                    {"sid": profile_id},
                    channel="write",
                )
                await self._db.query(
                    'DELETE FROM "student_settings" WHERE student_id = :sid',
                    {"sid": profile_id},
                    channel="write",
                )
                await self._db.delete("students", profile_id)
        elif role_name == "tutor":
            profiles = await self._db.query(
                'SELECT id FROM "tutors" WHERE user_id = :uid',
                {"uid": token.user_id},
            )
            if profiles:
                profile_id = profiles[0]["id"]
                lesson_ids = await self._db.query(
                    'SELECT id FROM "lessons" WHERE tutor_id = :tid',
                    {"tid": profile_id},
                )
                for lid in lesson_ids:
                    await self._db.query(
                        'DELETE FROM "lesson_participants" WHERE lesson_id = :lid',
                        {"lid": lid["id"]},
                        channel="write",
                    )
                await self._db.query(
                    'DELETE FROM "lessons" WHERE tutor_id = :tid',
                    {"tid": profile_id},
                    channel="write",
                )
                await self._db.query(
                    'DELETE FROM "bookings" WHERE tutor_id = :tid',
                    {"tid": profile_id},
                    channel="write",
                )
                await self._db.query(
                    'DELETE FROM "configurations" WHERE tutor_id = :tid',
                    {"tid": profile_id},
                    channel="write",
                )
                await self._db.query(
                    'DELETE FROM "tutor_settings" WHERE tutor_id = :tid',
                    {"tid": profile_id},
                    channel="write",
                )
                await self._db.delete("tutors", profile_id)
        elif role_name == "admin":
            profiles = await self._db.query(
                'SELECT id FROM "admins" WHERE user_id = :uid',
                {"uid": token.user_id},
            )
            if profiles:
                # Защита от потери управления: у приложения нет способа
                # вернуть админ-доступ через API, поэтому последнего
                # администратора нельзя удалить.
                count_rows = await self._db.query(
                    'SELECT COUNT(*) AS cnt FROM "admins"',
                    {},
                )
                if count_rows and count_rows[0]["cnt"] <= 1:
                    raise ConflictError("Cannot delete the last administrator account")
                await self._db.delete("admins", profiles[0]["id"])

        # Уведомления ссылаются на users FK без каскада: чистим до
        # удаления пользователя, чтобы DELETE не упёрся в констрейнт.
        await self._db.query(
            'DELETE FROM "notifications" WHERE user_id = :uid',
            {"uid": token.user_id},
            channel="write",
        )
        await self._db.delete("users", token.user_id)
        return DeleteMeResponse(ok=True)
