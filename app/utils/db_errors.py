"""Распознавание ошибок БД по сообщению драйвера/адаптера.

Адаптер event-infra оборачивает ошибки в Exception с текстом PostgreSQL,
поэтому типизировать их на уровне приложения нельзя — приходится
анализировать сообщение. Хелперы централизуют эти проверки, чтобы не
дублировать хрупкие подстроки по сценариям.
"""


def _msg(exc: Exception) -> str:
    return str(exc).lower()


def is_unique_violation(exc: Exception) -> bool:
    """Нарушение уникальности (unique/duplicate/констрейнт uq_)."""
    msg = _msg(exc)
    return "unique" in msg or "duplicate" in msg or "uq_" in msg


def is_overlap_violation(exc: Exception) -> bool:
    """Нарушение exclusion-констрейнта (пересечение интервалов)."""
    msg = _msg(exc)
    return "overlap" in msg or "exclusion" in msg or "conflicting key" in msg

