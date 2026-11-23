from pydantic import BaseModel
import datetime
from core import BaseScenario, NotFoundError, ValidationError, ConflictError, register_scenario, tracked_scenario
from core.utils.security import extract_token_info
from app.core.exceptions import ForbiddenError
from app.utils.json_codec import serialize_for_db, parse_row, parse_rows, parse_int_list
from app.utils.db_errors import is_overlap_violation, is_unique_violation
from app.utils.safe_parse import parse_iso_time
from app.utils.bookings import validate_booking_times, check_booking_overlap, build_booking_update_data, validate_weekday

from core.dto import BaseDTO

VALID_ACCESS_RULES = {"EVERYONE", "ONLY", "ALL_EXCEPT", "NOBODY"}
TARGETS_REQUIRED_RULES = {"ONLY", "ALL_EXCEPT"}


def parse_booking_time(value: str, field: str) -> datetime.time:
    """Время брони: как time, но допустим «до конца суток» — "24:00" (хранится как 23:59:59.999999)."""
    if value in ("24:00", "24:00:00"):
        return datetime.time.max
    return parse_iso_time(value, field)


async def _validate_access_targets(db, tutor_id: int, access_rule: str, access_targets: list[int] | None) -> None:
    if access_rule not in TARGETS_REQUIRED_RULES:
        return
    if not access_targets:
        raise ValidationError(f"access_targets is required for access_rule '{access_rule}'")
    rows = await db.query(
        'SELECT student_id FROM "configurations" WHERE tutor_id = :tid',
        {"tid": tutor_id},
    )
    valid_ids = {r["student_id"] for r in rows}
    invalid = [sid for sid in access_targets if sid not in valid_ids]
    if invalid:
        raise ValidationError(f"Invalid access_targets: student IDs {invalid} are not linked to this tutor")


class TutorGetMyBookingsDTO(BaseDTO):
    weekday: str | None = None


class TutorBookingItem(BaseModel):
    booking_id: int
    weekday: str
    start_time: str
    end_time: str
    access_rule: str
    access_targets: list[int] | None


class TutorGetMyBookingsResponse(BaseModel):
    bookings: list[TutorBookingItem]
    total: int


@register_scenario("tutor_get_my_bookings", dto=TutorGetMyBookingsDTO, response=TutorGetMyBookingsResponse)
@tracked_scenario("tutor_get_my_bookings")
class TutorGetMyBookingsScenario(BaseScenario):
    async def execute(self, dto: TutorGetMyBookingsDTO) -> TutorGetMyBookingsResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        if dto.weekday:
            bookings = await self._db.query(
                'SELECT * FROM "bookings" WHERE tutor_id = :tid AND weekday = :wd ORDER BY start_time LIMIT :lim OFFSET :off',
                {"tid": tutor_id, "wd": dto.weekday, "lim": dto.limit, "off": dto.offset},
            )
            count_rows = await self._db.query(
                'SELECT COUNT(*) AS cnt FROM "bookings" WHERE tutor_id = :tid AND weekday = :wd',
                {"tid": tutor_id, "wd": dto.weekday},
            )
        else:
            bookings = await self._db.query(
                'SELECT * FROM "bookings" WHERE tutor_id = :tid ORDER BY start_time LIMIT :lim OFFSET :off',
                {"tid": tutor_id, "lim": dto.limit, "off": dto.offset},
            )
            count_rows = await self._db.query(
                'SELECT COUNT(*) AS cnt FROM "bookings" WHERE tutor_id = :tid',
                {"tid": tutor_id},
            )

        total = count_rows[0]["cnt"] if count_rows else 0

        result = []
        for b in parse_rows("bookings", bookings):
            result.append(TutorBookingItem(
                booking_id=b["id"],
                weekday=b["weekday"],
                start_time=str(b["start_time"]),
                end_time=str(b["end_time"]),
                access_rule=b["access_rule"],
                access_targets=b.get("access_targets"),
            ))

        return TutorGetMyBookingsResponse(bookings=result, total=total)


class TutorCreateBookingDTO(BaseDTO):
    weekday: str
    start_time: str
    end_time: str
    access_rule: str = "EVERYONE"
    access_targets: list[int] | None = None
    booking_metadata: dict | None = None


class TutorCreateBookingResponse(BaseModel):
    booking_id: int
    tutor_id: int
    weekday: str
    start_time: str
    end_time: str
    access_rule: str
    access_targets: list[int] | None
    booking_metadata: dict | None


@register_scenario("tutor_create_booking", dto=TutorCreateBookingDTO, response=TutorCreateBookingResponse)
@tracked_scenario("tutor_create_booking")
class TutorCreateBookingScenario(BaseScenario):
    async def execute(self, dto: TutorCreateBookingDTO) -> TutorCreateBookingResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        start_time = parse_booking_time(dto.start_time, "start_time")
        end_time = parse_booking_time(dto.end_time, "end_time")
        validate_booking_times(start_time, end_time)
        validate_weekday(dto.weekday)

        if dto.access_rule not in VALID_ACCESS_RULES:
            raise ValidationError(f"Invalid access_rule: {dto.access_rule}. Must be one of: {', '.join(sorted(VALID_ACCESS_RULES))}")

        await _validate_access_targets(self._db, tutor_id, dto.access_rule, dto.access_targets)

        overlapping = await self._db.query(
            'SELECT id FROM "bookings" WHERE tutor_id = :tid AND weekday = :wd AND start_time < :et AND end_time > :st',
            {"tid": tutor_id, "wd": dto.weekday, "et": end_time, "st": start_time},
        )
        check_booking_overlap(overlapping)

        booking_base = build_booking_update_data({
            "tutor_id": tutor_id,
            "weekday": dto.weekday,
            "start_time": start_time,
            "end_time": end_time,
            "access_rule": dto.access_rule,
            "access_targets": dto.access_targets,
            "booking_metadata": dto.booking_metadata,
        })
        booking_base = serialize_for_db("bookings", booking_base)
        try:
            booking = await self._db.create("bookings", booking_base)
        except Exception as e:
            if is_overlap_violation(e) or is_unique_violation(e):
                raise ConflictError("Booking overlaps with an existing one")
            raise
        booking = parse_row("bookings", booking)

        return TutorCreateBookingResponse(
            booking_id=booking["id"],
            tutor_id=booking["tutor_id"],
            weekday=booking["weekday"],
            start_time=str(booking["start_time"]),
            end_time=str(booking["end_time"]),
            access_rule=booking["access_rule"],
            access_targets=booking.get("access_targets"),
            booking_metadata=booking.get("booking_metadata"),
        )


class TutorUpdateBookingDTO(BaseDTO):
    booking_id: int | None = None
    weekday: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    access_rule: str | None = None
    access_targets: list[int] | None = None
    booking_metadata: dict | None = None


class TutorUpdateBookingResponse(BaseModel):
    booking_id: int
    tutor_id: int
    weekday: str
    start_time: str
    end_time: str
    access_rule: str
    access_targets: list[int] | None
    booking_metadata: dict | None


@register_scenario("tutor_update_booking", dto=TutorUpdateBookingDTO, response=TutorUpdateBookingResponse)
@tracked_scenario("tutor_update_booking")
class TutorUpdateBookingScenario(BaseScenario):
    async def execute(self, dto: TutorUpdateBookingDTO) -> TutorUpdateBookingResponse:
        if dto.booking_id is None:
            raise ValidationError("booking_id is required")
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        booking_rows = await self._db.query(
            'SELECT * FROM "bookings" WHERE id = :bid',
            {"bid": dto.booking_id},
        )
        if not booking_rows:
            raise NotFoundError(f"Booking {dto.booking_id} not found")
        booking = booking_rows[0]

        if booking["tutor_id"] != tutor_id:
            raise ForbiddenError("You can only update your own bookings")

        booking = parse_row("bookings", booking)
        if dto.weekday is not None:
            validate_weekday(dto.weekday)
        new_weekday = dto.weekday if dto.weekday else booking["weekday"]
        new_start = parse_booking_time(dto.start_time, "start_time") if dto.start_time else booking["start_time"]
        new_end = parse_booking_time(dto.end_time, "end_time") if dto.end_time else booking["end_time"]

        time_changed = (
            str(new_start) != str(booking["start_time"]) or
            str(new_end) != str(booking["end_time"]) or
            new_weekday != booking["weekday"]
        )

        if time_changed:
            validate_booking_times(new_start, new_end)
            overlapping = await self._db.query(
                'SELECT id FROM "bookings" WHERE tutor_id = :tid AND weekday = :wd AND start_time < :et AND end_time > :st AND id != :bid',
                {"tid": tutor_id, "wd": new_weekday, "et": new_end, "st": new_start, "bid": dto.booking_id},
            )
            check_booking_overlap(overlapping)

        if dto.access_rule is not None and dto.access_rule not in VALID_ACCESS_RULES:
            raise ValidationError(f"Invalid access_rule: {dto.access_rule}. Must be one of: {', '.join(sorted(VALID_ACCESS_RULES))}")

        effective_rule = dto.access_rule if dto.access_rule is not None else booking["access_rule"]
        effective_targets = dto.access_targets if dto.access_targets is not None else parse_int_list(booking.get("access_targets"))
        if effective_rule in TARGETS_REQUIRED_RULES:
            await _validate_access_targets(self._db, tutor_id, effective_rule, effective_targets)

        update_fields = {}
        if dto.weekday is not None:
            update_fields["weekday"] = dto.weekday
        if dto.start_time is not None:
            update_fields["start_time"] = new_start
        if dto.end_time is not None:
            update_fields["end_time"] = new_end
        if dto.access_rule is not None:
            update_fields["access_rule"] = dto.access_rule
        if dto.access_rule is not None and effective_rule not in TARGETS_REQUIRED_RULES:
            update_fields["access_targets"] = []
        elif dto.access_targets is not None:
            update_fields["access_targets"] = dto.access_targets
        if dto.booking_metadata is not None:
            update_fields["booking_metadata"] = dto.booking_metadata

        if update_fields:
            final_update = build_booking_update_data(update_fields)
            final_update = serialize_for_db("bookings", final_update)
            updated = await self._db.update("bookings", dto.booking_id, final_update)
            updated = parse_row("bookings", updated)
        else:
            updated = booking

        return TutorUpdateBookingResponse(
            booking_id=updated["id"],
            tutor_id=updated["tutor_id"],
            weekday=updated["weekday"],
            start_time=str(updated["start_time"]),
            end_time=str(updated["end_time"]),
            access_rule=updated["access_rule"],
            access_targets=updated.get("access_targets"),
            booking_metadata=updated.get("booking_metadata"),
        )


class TutorDeleteBookingDTO(BaseDTO):
    booking_id: int


class TutorDeleteBookingResponse(BaseModel):
    ok: bool


@register_scenario("tutor_delete_booking", dto=TutorDeleteBookingDTO, response=TutorDeleteBookingResponse)
@tracked_scenario("tutor_delete_booking")
class TutorDeleteBookingScenario(BaseScenario):
    async def execute(self, dto: TutorDeleteBookingDTO) -> TutorDeleteBookingResponse:
        token = extract_token_info(dto.access_token)

        tutors = await self._db.query(
            'SELECT id FROM "tutors" WHERE user_id = :uid',
            {"uid": token.user_id},
        )
        if not tutors:
            raise NotFoundError("Tutor profile not found")
        tutor_id = tutors[0]["id"]

        booking_rows = await self._db.query(
            'SELECT * FROM "bookings" WHERE id = :bid',
            {"bid": dto.booking_id},
        )
        if not booking_rows:
            raise NotFoundError(f"Booking {dto.booking_id} not found")
        booking = booking_rows[0]

        if booking["tutor_id"] != tutor_id:
            raise ForbiddenError("You can only delete your own bookings")

        await self._db.delete("bookings", dto.booking_id)
        return TutorDeleteBookingResponse(ok=True)
