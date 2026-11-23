"""Файловый лог фронтенда (logs/frontend.log).

Единая точка правды о пути и формате: писать сюда умеет
app/scenarios/system/write_logs.py, читать — сценарий системного журнала.
Лог пишется браузером параллельно с чтением, поэтому битые
и неполные строки пропускаются, а не роняют выгрузку.
"""
import json
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "frontend.log"

# Читаем только хвост: файл растёт неограничен, а журнал в UI — свежий.
TAIL_BYTES = 2 * 1024 * 1024


def read_log_entries(path: str | Path | None = None, tail_bytes: int = TAIL_BYTES) -> list[dict]:
    """Валидные записи лога от новых к старым.

    Первая строка хвоста может быть обрезана seek — такие строки
    не парсятся и молча пропускаются.
    """
    target = Path(path) if path else LOG_FILE
    if not target.exists():
        return []

    try:
        with open(target, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - tail_bytes))
            chunk = f.read()
    except OSError:
        return []

    entries = []
    for line in chunk.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("ts"):
            entries.append(row)

    entries.reverse()
    return entries


def write_log_entries(entries: list[dict]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
