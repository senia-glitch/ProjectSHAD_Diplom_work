# Единая точка входа для JSON-кодека.
# Новый код: используйте serialize_for_db / parse_row / parse_rows / parse_int_list
# из app.utils.json_codec. Старая serialize_json_fields оставлена для
# обратной совместимости и делегирует в dumps_value.

from app.utils.json_codec import dumps_value


def serialize_json_fields(data: dict, *field_names: str) -> dict:
    """DEPRECATED: используйте serialize_for_db(table, data).

    Оставлена, чтобы не ломать существующие импорты.
    Сериализует указанные поля dict в JSON-строки для asyncpg JSON-колонок.
    """
    result = dict(data)
    for key in field_names:
        if key in result:
            result[key] = dumps_value(result[key])
    return result


__all__ = [
    "serialize_json_fields",
]
