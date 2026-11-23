from typing import Optional, List, Dict, Any
from datetime import datetime, time

from pydantic import NaiveDatetime
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, UniqueConstraint

# Existing event-infra CRUD payloads carry JSON as encoded strings. Both the
# native Python form and the legacy encoded form are valid storage inputs;
# application DTOs still expose lists/dicts through app.utils.json_codec.
metadata = SQLModel.metadata


# ============================================
# 1. РОЛИ
# ============================================

class Role(SQLModel, table=True):
    """Роли пользователей."""
    __tablename__ = "roles"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True)


# ============================================
# 2. ПОЛЬЗОВАТЕЛИ
# ============================================

class User(SQLModel, table=True):
    """Пользователи системы."""
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)
    refresh_token: Optional[str] = Field(default=None, max_length=500)

    role_id: int = Field(foreign_key="roles.id")
    username: str = Field(max_length=50, unique=True)
    personal_number: str = Field(max_length=50, unique=True)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=255)
    email: str = Field(max_length=255, unique=True)

    gender: Optional[str] = Field(default=None, max_length=20)
    additional_info: Optional[str] = None


# ============================================
# 3. ПРОФИЛИ
# ============================================

class Admin(SQLModel, table=True):
    """Администраторы."""
    __tablename__ = "admins"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)


class Student(SQLModel, table=True):
    """Ученики."""
    __tablename__ = "students"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)


class Tutor(SQLModel, table=True):
    """Репетиторы."""
    __tablename__ = "tutors"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)


# ============================================
# 4. НАСТРОЙКИ
# ============================================

class StudentSettings(SQLModel, table=True):
    """Настройки ученика."""
    __tablename__ = "student_settings"
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id", unique=True)

    status: str = Field(default="ACTIVE", max_length=20)
    timezone_offset: int = Field(default=0)
    schedule_view: str = Field(default="INFORMATIVE", max_length=20)
    display_time_from: str = Field(default="00:00", max_length=5)
    display_time_to: str = Field(default="23:59", max_length=5)


class TutorSettings(SQLModel, table=True):
    """Настройки репетитора."""
    __tablename__ = "tutor_settings"
    id: Optional[int] = Field(default=None, primary_key=True)
    tutor_id: int = Field(foreign_key="tutors.id", unique=True)

    hourly_rate: float = Field(default=0.0)
    discount: float = Field(default=0.0)
    timezone_offset: int = Field(default=0)
    work_status: str = Field(default="WORKING", max_length=20)
    schedule_type: str = Field(default="INFORMATIVE", max_length=20)
    display_time_from: str = Field(default="00:00", max_length=5)
    display_time_to: str = Field(default="23:59", max_length=5)
    self_booking_mode: str = Field(default="YES", max_length=20)
    self_booking_whitelist: Optional[List[int] | str] = Field(default=None, sa_type=JSON)
    booking_lead_time_hours: int = Field(default=24)
    cancellation_lead_time_hours: int = Field(default=24)
    default_links: Optional[List[Dict[str, str]] | str] = Field(default=None, sa_type=JSON)


# ============================================
# 5. КОНФИГУРАЦИИ (связь ученик-репетитор)
# ============================================

class Configuration(SQLModel, table=True):
    """Конфигурация связи ученик-репетитор."""
    __tablename__ = "configurations"
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id")
    tutor_id: int = Field(foreign_key="tutors.id")

    hourly_rate: float = Field(default=0.0)
    discount: float = Field(default=0.0)
    slot_step_minutes: int = Field(default=60)
    allow_self_booking: bool = Field(default=True)
    booking_lead_time_hours: int = Field(default=24)
    cancellation_lead_time_hours: int = Field(default=24)
    notifications_enabled: bool = Field(default=True)
    notification_lead_time_hours: int = Field(default=24)
    default_links: Optional[List[Dict[str, str]] | str] = Field(default=None, sa_type=JSON)
    allow_unpaid_lesson: bool = Field(default=False)
    student_notes: Optional[str] = None
    link_visibility_enabled: bool = Field(default=False)
    link_lead_time_minutes: int = Field(default=0)

    __table_args__ = (
        UniqueConstraint("student_id", "tutor_id", name="uq_student_tutor"),
    )


# ============================================
# 6. БРОНИ (повторяющиеся блокировки времени)
# ============================================

class Booking(SQLModel, table=True):
    """Бронь — повторяющаяся блокировка времени репетитора."""
    __tablename__ = "bookings"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)
    updated_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)

    tutor_id: int = Field(foreign_key="tutors.id")
    weekday: str = Field(max_length=20)
    start_time: time
    end_time: time

    access_rule: str = Field(default="EVERYONE", max_length=20)
    access_targets: Optional[List[int] | str] = Field(default=None, sa_type=JSON)
    booking_metadata: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)


# ============================================
# 7. УРОКИ
# ============================================

class Lesson(SQLModel, table=True):
    """Уроки."""
    __tablename__ = "lessons"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)
    updated_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)

    tutor_id: int = Field(foreign_key="tutors.id")
    start_time: NaiveDatetime
    end_time: NaiveDatetime
    created_by_id: int

    is_group: bool = Field(default=False)
    status: str = Field(default="SCHEDULED", max_length=20)
    lesson_settings: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)
    lesson_links: Optional[List[Dict[str, str]] | str] = Field(default=None, sa_type=JSON)
    lesson_metadata: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)
    lesson_descriptions: Optional[str] = None


class LessonParticipant(SQLModel, table=True):
    """Участники урока."""
    __tablename__ = "lesson_participants"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)
    updated_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)

    lesson_id: int = Field(foreign_key="lessons.id")
    student_id: int = Field(foreign_key="students.id")

    participant_settings: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)
    participant_metadata: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)

    __table_args__ = (
        UniqueConstraint("lesson_id", "student_id", name="uq_lesson_participant"),
    )


# ============================================
# 8. УВЕДОМЛЕНИЯ
# ============================================

class Notification(SQLModel, table=True):
    """Уведомления пользователей."""
    __tablename__ = "notifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.now)

    user_id: int = Field(foreign_key="users.id", index=True)
    type: str = Field(max_length=50)
    payload: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)
    read_at: Optional[NaiveDatetime] = Field(default=None)


# ============================================
# АВТОСБОР СХЕМ
# ============================================

def get_all_schemas():
    """Автоматически собирает все SQLModel-таблицы из текущего модуля."""
    import sys
    module = sys.modules[__name__]
    schemas = {}
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, SQLModel)
            and attr != SQLModel
            and hasattr(attr, "__table__")
        ):
            schemas[attr.__tablename__] = attr
    return schemas
