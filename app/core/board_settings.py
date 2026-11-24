"""Ограничения совместной доски. Значения читаются из окружения при старте (префикс BOARD_)."""
import os


def _int_env(name, default, low, high):
    raw = os.getenv(name, '').strip()
    value = int(raw) if raw else default
    if not low <= value <= high:
        raise ValueError(f'{name} must be in [{low}, {high}]')
    return value


class BoardSettings:
    """Ограничения совместной доски. Значения читаются из окружения/.env при старте."""

    def __init__(self):
        self.max_peers = _int_env('BOARD_MAX_PEERS', 15, 1, 1000)
        self.max_strokes = _int_env('BOARD_MAX_STROKES', 20000, 1, 1_000_000)
        # Объём доски: сумма координат всех штрихов (≈ 6 байт памяти на число).
        self.max_values = _int_env('BOARD_MAX_VALUES', 2_000_000, 1000, 100_000_000)
        self.messages_per_second = _int_env('BOARD_MESSAGES_PER_SECOND', 40, 1, 10000)
        self.max_message_bytes = _int_env('BOARD_MAX_MESSAGE_BYTES', 262144, 1024, 16 * 1024 * 1024)
        self.creates_per_minute = _int_env('BOARD_CREATES_PER_MINUTE', 20, 1, 10000)
        self.send_queue = _int_env('BOARD_SEND_QUEUE', 2000, 16, 100000)
        self.chat_keep = _int_env('BOARD_CHAT_KEEP', 300, 1, 10000)          # сообщений в истории чата
        self.max_import_bytes = _int_env('BOARD_MAX_IMPORT_BYTES', 16 * 1024 * 1024, 1024, 256 * 1024 * 1024)
        self.imports_per_minute = _int_env('BOARD_IMPORTS_PER_MINUTE', 10, 1, 10000)
        self.autosave_minutes = _int_env('BOARD_AUTOSAVE_MINUTES', 2, 1, 1440)
        self.retention_days = _int_env('BOARD_RETENTION_DAYS', 365, 1, 3650)  # удалить доску без входов
        # Защита входа.
        self.handshakes_per_minute = _int_env('BOARD_JOINS_PER_MINUTE', 30, 1, 10000)
        self.ip_code_failures = _int_env('BOARD_IP_CODE_FAILURES', 10, 1, 10000)
        self.board_code_failures = _int_env('BOARD_BOARD_CODE_FAILURES', 30, 1, 100000)
        self.code_failure_window = _int_env('BOARD_CODE_FAILURE_WINDOW_SECONDS', 900, 10, 86400)
        self.code_lock_seconds = _int_env('BOARD_CODE_LOCK_SECONDS', 900, 10, 86400)
        self.global_code_failures = _int_env('BOARD_GLOBAL_CODE_FAILURES', 300, 1, 1_000_000)
        # Разрешённые Origin для WebSocket через запятую (https://board.example.com).
        # Пусто — допускается только тот же хост, что в заголовке Host (тот же сайт).
        self.allowed_origins = {o.strip().rstrip('/').lower()
                                for o in os.getenv('BOARD_ALLOWED_ORIGINS', '').split(',') if o.strip()}


board_settings = BoardSettings()
