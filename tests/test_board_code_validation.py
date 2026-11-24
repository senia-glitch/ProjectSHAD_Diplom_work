"""Свой код доски проверяется при разборе запроса: неверный код — 422 с причиной, а не 500."""
import pytest
from pydantic import ValidationError

from app.api.v1.routes.boards import CreateBody


def test_short_custom_code_is_rejected_with_reason():
    with pytest.raises(ValidationError) as error:
        CreateBody(title="Урок", code="abc")
    assert "Код: от 6 до 32 букв или цифр" in str(error.value)


def test_custom_code_is_normalized_and_empty_means_generated():
    assert CreateBody(code="abc-def 12").code == "ABCDEF12"
    assert CreateBody(code="   ").code is None
