from typing import Optional, List, Dict, Any
from datetime import datetime, time

from pydantic import NaiveDatetime
from app.utils.clock import utc_now
from sqlmodel import SQLModel, Field
import sqlalchemy as sa
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
    created_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)
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
    # Связь с этим учеником создаётся только после его явного согласия.
    require_link_consent: bool = Field(default=True)


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
    # Значение по умолчанию для новых связей: запись ученика без подтверждения.
    auto_confirm_bookings: bool = Field(default=True)
    # Связь с этим репетитором создаётся только после его явного согласия.
    require_link_consent: bool = Field(default=True)
    # Отпуск/болезнь с границами (наивный UTC). Пока период идёт, запись закрыта,
    # уроки периода помечаются, начавшиеся закрывает система.
    absence_status: Optional[str] = Field(default=None, max_length=20)
    absence_from: Optional[NaiveDatetime] = None
    absence_to: Optional[NaiveDatetime] = None


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
    # Запись ученика сразу подтверждена (False — заявка ждёт решения репетитора).
    auto_confirm_bookings: bool = Field(default=True)
    # ACTIVE — связь действует; PENDING — ждёт согласия второй стороны.
    status: str = Field(default="ACTIVE", max_length=20)
    requested_by: Optional[str] = Field(default=None, max_length=20)
    requested_at: Optional[NaiveDatetime] = None

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
    created_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)
    updated_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)

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
    created_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)
    updated_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)

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
    # История смены статуса: [{status, by: system|tutor|student, actor_user_id, at, reason, meta}].
    # Отмена, отклонение заявки и закрытие системой фиксируются здесь, а не в lesson_metadata
    # (её репетитор может перезаписать правкой урока).
    status_history: Optional[List[Dict[str, Any]] | str] = Field(default=None, sa_type=JSON)


class LessonParticipant(SQLModel, table=True):
    """Участники урока."""
    __tablename__ = "lesson_participants"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)
    updated_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)

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
    created_at: Optional[NaiveDatetime] = Field(default_factory=utc_now)

    user_id: int = Field(foreign_key="users.id", index=True)
    type: str = Field(max_length=50)
    payload: Optional[Dict[str, Any] | str] = Field(default=None, sa_type=JSON)
    read_at: Optional[NaiveDatetime] = Field(default=None)


# ============================================
# 9. ТЕСТИРОВАНИЕ (тесты репетитора, доступ ученикам, попытки)
# ============================================

def _tz(nullable=False):
    return sa.Column(sa.DateTime(timezone=True), nullable=nullable)


class Quiz(SQLModel, table=True):
    """Тест репетитора. Задания — JSON-массив; изменение повышает версию."""
    __tablename__ = "quizzes"
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    title: str = Field(max_length=200)
    description: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    tasks: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    version: int = Field(default=1)
    good_percent: int = Field(default=60)
    excellent_percent: int = Field(default=85)
    created_at: datetime = Field(sa_column=_tz())
    updated_at: datetime = Field(sa_column=_tz())


class QuizAccess(SQLModel, table=True):
    """Доступ ученика (users.id) к тесту; репетитор включает и выключает его в любой момент."""
    __tablename__ = "quiz_access"
    __table_args__ = (sa.UniqueConstraint("quiz_id", "student_id", name="uq_quiz_access"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False))
    student_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    granted_at: datetime = Field(sa_column=_tz())


class QuizAttempt(SQLModel, table=True):
    """Попытка прохождения: ответы, результаты автопроверки и оценка репетитора."""
    __tablename__ = "quiz_attempts"
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True))
    student_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    quiz_version: int
    answers: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    results: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    score: float
    max_score: float
    auto_grade: Optional[str] = Field(default=None, max_length=32)
    teacher_grade: Optional[str] = Field(default=None, max_length=32)
    teacher_comment: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    submitted_at: datetime = Field(sa_column=_tz())
    reviewed_at: Optional[datetime] = Field(default=None, sa_column=_tz(nullable=True))


# ============================================
# 10. ДОСКИ (совместное рисование в реальном времени)
# ============================================

class Board(SQLModel, table=True):
    """Доска репетитора. Вход по коду; сервер хранит только HMAC кода."""
    __tablename__ = "boards"
    id: str = Field(sa_column=sa.Column(sa.String(40), primary_key=True))
    owner_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    title: str = Field(sa_column=sa.Column(sa.String(120), nullable=False, server_default=""))
    created_at: Optional[datetime] = Field(default=None, sa_column=sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    code_lookup: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(64), nullable=True, unique=True))
    creator_key: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(40), nullable=True))
    last_active_at: Optional[datetime] = Field(default=None, sa_column=sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True))
    saved_at: Optional[datetime] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True))


class BoardStroke(SQLModel, table=True):
    """Снимок штрихов доски; перезаписывается автосохранением, порядок — по id."""
    __tablename__ = "board_strokes"
    __table_args__ = (sa.Index("ix_board_strokes_board_id_id", "board_id", "id"),)
    id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger, primary_key=True, autoincrement=True))
    board_id: str = Field(sa_column=sa.Column(sa.String(40), sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False))
    stroke_key: str = Field(sa_column=sa.Column(sa.String(40), nullable=False))
    author_key: str = Field(sa_column=sa.Column(sa.String(40), nullable=False))
    tool: str = Field(sa_column=sa.Column(sa.String(16), nullable=False))
    color: str = Field(sa_column=sa.Column(sa.String(7), nullable=False))
    width: int = Field(sa_column=sa.Column(sa.SmallInteger, nullable=False))
    points: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    created_at: Optional[datetime] = Field(default=None, sa_column=sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))


class BoardChatMessage(SQLModel, table=True):
    """Сообщения чата доски (хранятся последние N)."""
    __tablename__ = "board_chat_messages"
    __table_args__ = (sa.Index("ix_board_chat_messages_board_id_id", "board_id", "id"),)
    id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger, primary_key=True, autoincrement=True))
    board_id: str = Field(sa_column=sa.Column(sa.String(40), sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False))
    author_key: str = Field(sa_column=sa.Column(sa.String(40), nullable=False))
    name: str = Field(sa_column=sa.Column(sa.String(32), nullable=False))
    color: str = Field(sa_column=sa.Column(sa.String(7), nullable=False))
    text: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    created_at: Optional[datetime] = Field(default=None, sa_column=sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))


class BoardMember(SQLModel, table=True):
    """Кто входил на доску (повторный вход без кода); banned — исключён владельцем."""
    __tablename__ = "board_members"
    board_id: str = Field(sa_column=sa.Column(sa.String(40), sa.ForeignKey("boards.id", ondelete="CASCADE"), primary_key=True))
    author_key: str = Field(sa_column=sa.Column(sa.String(40), primary_key=True))
    banned: bool = Field(default=False, sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.false()))
    joined_at: Optional[datetime] = Field(default=None, sa_column=sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))


# ============================================
# 11. БЛОГ РЕПЕТИТОРА
# ============================================

class BlogPost(SQLModel, table=True):
    """Запись личного блога репетитора (Markdown). Черновик виден только автору."""
    __tablename__ = "blog_posts"
    __table_args__ = (sa.Index("ix_blog_posts_status_published", "status", "published_at"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    title: str = Field(max_length=200)
    body: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    tags: str = Field(sa_column=sa.Column(sa.Text, nullable=False, server_default="[]"))
    status: str = Field(default="draft", max_length=16)
    pinned: bool = Field(default=False, sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.false()))
    created_at: datetime = Field(sa_column=_tz())
    updated_at: datetime = Field(sa_column=_tz())
    published_at: Optional[datetime] = Field(default=None, sa_column=_tz(nullable=True))


class BlogComment(SQLModel, table=True):
    """Комментарий к опубликованной записи; пишет вошедший пользователь."""
    __tablename__ = "blog_comments"
    __table_args__ = (sa.Index("ix_blog_comments_post_id_id", "post_id", "id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False))
    author_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    text: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    created_at: datetime = Field(sa_column=_tz())


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
