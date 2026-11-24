"""Общие помощники модуля тестирования: ошибки валидации, JSON, время, очистка HTML."""
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from html import escape
from core import CoreError


class BadRequestError(CoreError):
    def __init__(self, message):
        super().__init__(message, code=3002, http_status=422)


def now():
    return datetime.now(timezone.utc)


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def loads(value, default=None):
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


ALLOWED_TAGS = {'b', 'strong', 'i', 'em', 'u', 's', 'p', 'br', 'ul', 'ol', 'li', 'h3', 'blockquote', 'code'}


class _Sanitizer(HTMLParser):
    """Оставляет только простые теги форматирования без атрибутов."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        elif tag in ALLOWED_TAGS and not self.skip:
            self.out.append(f'<{tag}>' if tag != 'br' else '<br>')
            if tag != 'br':
                self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        elif tag in self.stack and not self.skip:
            while self.stack:
                top = self.stack.pop()
                self.out.append(f'</{top}>')
                if top == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data))

    def result(self):
        return ''.join(self.out + [f'</{t}>' for t in reversed(self.stack)])


def sanitize_html(value, limit=20000):
    parser = _Sanitizer()
    parser.feed(str(value or '')[:limit])
    parser.close()
    return parser.result()
