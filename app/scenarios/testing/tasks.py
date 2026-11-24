"""Типы заданий: проверка структуры, выдача ученику без ответов и автопроверка.

Задание: {id, kind, variant, prompt, points, data, answer}.
`data` видит ученик, `answer` (необязательный) — только преподаватель.
Чистые функции без БД и HTTP; не являются сценариями core.
"""
import random
import re
import uuid

KINDS = {
    'choice': {'single', 'multiple', 'binary', 'dropdown', 'multi_dropdown'},
    'matching': {'columns', 'dropdown', 'drag', 'lines', 'multi'},
    'fill': {'single', 'multi', 'inline', 'inline_select', 'number', 'formula', 'table'},
    'open': {'short', 'long', 'number', 'rich', 'blocks'},
    'ordering': {'vertical', 'horizontal', 'buttons', 'numbered', 'slots'},
    'categorize': {'two', 'many', 'drag', 'dropdown', 'multi'},
    'selection': {'one', 'many', 'position', 'place_labels', 'name', 'scheme'},
    'connecting': {'single', 'many', 'hub', 'network', 'directed'},
    'editing': {'rewrite', 'highlight', 'replace', 'delete', 'reorder', 'insert'},
}
GRADES = ('удовлетворительно', 'хорошо', 'замечательно')
MAX_TASKS = 100
MAX_TEXT = 5000
MAX_PROMPT = 20000  # Markdown-описание задания; медиа только по внешним ссылкам


class TaskError(ValueError):
    """Ошибка структуры задания; текст безопасен для показа преподавателю."""


# ---------- общие помощники ----------

def _str(value, name, *, required=True, limit=MAX_TEXT):
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise TaskError(f'{name}: ожидается текст')
    value = value.strip()
    if required and not value:
        raise TaskError(f'{name}: заполните поле')
    if len(value) > limit:
        raise TaskError(f'{name}: слишком длинный текст')
    return value


def _list(value, name, *, min_len=0, max_len=200):
    if not isinstance(value, list):
        raise TaskError(f'{name}: ожидается список')
    if not min_len <= len(value) <= max_len:
        raise TaskError(f'{name}: нужно от {min_len} до {max_len} элементов')
    return value


def _strings(value, name, *, min_len=1, max_len=200, limit=500):
    return [_str(v, f'{name}[{i + 1}]', limit=limit) for i, v in enumerate(_list(value, name, min_len=min_len, max_len=max_len))]


def _items(value, name, *, min_len=1, max_len=100, limit=500, extra=()):
    """Список {id, text} с уникальными id; id генерируется, если не задан."""
    result, seen = [], set()
    for i, raw in enumerate(_list(value, name, min_len=min_len, max_len=max_len)):
        if isinstance(raw, str):
            raw = {'text': raw}
        if not isinstance(raw, dict):
            raise TaskError(f'{name}[{i + 1}]: неверный элемент')
        item_id = str(raw.get('id') or uuid.uuid4().hex[:8])[:40]
        if item_id in seen:
            raise TaskError(f'{name}: повторяющийся идентификатор')
        seen.add(item_id)
        item = {'id': item_id, 'text': _str(raw.get('text'), f'{name}[{i + 1}]', limit=limit)}
        for key in extra:
            if key in ('x', 'y'):
                item[key] = _coord(raw.get(key), f'{name}[{i + 1}].{key}')
        result.append(item)
    return result


def _coord(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise TaskError(f'{name}: ожидается число 0–100') from None
    if not 0 <= number <= 100:
        raise TaskError(f'{name}: ожидается число 0–100')
    return round(number, 2)


def _indices(value, name, size):
    values = _list(value, name, max_len=size)
    if not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v < size for v in values):
        raise TaskError(f'{name}: неверный номер')
    return sorted(set(values))


def _ids(value, name, allowed):
    values = _list(value, name, max_len=len(allowed))
    if not all(isinstance(v, str) and v in allowed for v in values):
        raise TaskError(f'{name}: неизвестный элемент')
    return list(dict.fromkeys(values))


def _number(value, name, *, minimum=None):
    try:
        number = float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        raise TaskError(f'{name}: ожидается число') from None
    if number != number or abs(number) > 1e12 or (minimum is not None and number < minimum):
        raise TaskError(f'{name}: недопустимое число')
    return number


def tokens(text):
    return text.split()


def norm_text(value):
    return ' '.join(str(value or '').split()).casefold()


def norm_formula(value):
    text = str(value or '').casefold().replace('**', '^').replace('×', '*').replace('·', '*').replace('−', '-')
    return re.sub(r'\s+', '', text)


def parse_number(value):
    try:
        number = float(str(value).strip().replace(',', '.'))
    except (TypeError, ValueError):
        return None
    return number if number == number else None


# ---------- проверка структуры (преподаватель) ----------

def validate_tasks(raw_tasks):
    tasks = _list(raw_tasks, 'Задания', min_len=1, max_len=MAX_TASKS)
    result, seen = [], set()
    for index, raw in enumerate(tasks, start=1):
        try:
            task = validate_task(raw)
        except TaskError as error:
            raise TaskError(f'Задание {index}. {error}') from None
        if task['id'] in seen:
            task['id'] = uuid.uuid4().hex[:8]
        seen.add(task['id'])
        result.append(task)
    return result


def validate_task(raw):
    if not isinstance(raw, dict):
        raise TaskError('неверный формат')
    kind, variant = raw.get('kind'), raw.get('variant')
    if kind not in KINDS or variant not in KINDS[kind]:
        raise TaskError('неизвестный тип задания')
    data = raw.get('data') if isinstance(raw.get('data'), dict) else {}
    answer = raw.get('answer') if isinstance(raw.get('answer'), dict) else None
    task = {
        'id': str(raw.get('id') or uuid.uuid4().hex[:8])[:40],
        'kind': kind, 'variant': variant,
        'prompt': _str(raw.get('prompt'), 'Вопрос', limit=MAX_PROMPT),
        'points': _number(raw.get('points') or 0, 'Баллы', minimum=0),
    }
    task['data'], task['answer'] = VALIDATORS[kind](variant, data, answer)
    return task


def _v_choice(variant, data, answer):
    options = _strings(data.get('options'), 'Варианты', min_len=2, max_len=50)
    if variant == 'binary' and len(options) != 2:
        raise TaskError('в бинарном выборе ровно два варианта')
    if answer is not None:
        correct = _indices(answer.get('correct', []), 'Правильный ответ', len(options))
        if not correct:
            answer = None
        elif variant in ('single', 'binary', 'dropdown') and len(correct) != 1:
            raise TaskError('отметьте один правильный вариант')
        else:
            answer = {'correct': correct}
    return {'options': options}, answer


def _v_matching(variant, data, answer):
    left = _items(data.get('left'), 'Левая колонка', min_len=2, max_len=30)
    right = _items(data.get('right'), 'Правая колонка', min_len=2, max_len=30)
    if answer is not None:
        pairs = _pairs(answer.get('pairs', []), {i['id'] for i in left}, {i['id'] for i in right})
        if variant != 'multi' and len({a for a, _ in pairs}) != len(pairs):
            raise TaskError('элементу левой колонки можно сопоставить только один элемент')
        answer = {'pairs': pairs} if pairs else None
    return {'left': left, 'right': right}, answer


def _pairs(value, left_ids, right_ids):
    pairs = set()
    for pair in _list(value, 'Связи', max_len=len(left_ids) * len(right_ids)):
        if not (isinstance(pair, list) and len(pair) == 2 and pair[0] in left_ids and pair[1] in right_ids):
            raise TaskError('Связи: неверная пара')
        pairs.add((pair[0], pair[1]))
    return sorted([list(p) for p in pairs])


FIELD_RE = re.compile(r'\{\{([A-Za-z0-9_-]{1,40})\}\}')


def _v_fill(variant, data, answer):
    fields = []
    for i, raw in enumerate(_list(data.get('fields'), 'Поля', min_len=1, max_len=60)):
        if not isinstance(raw, dict):
            raise TaskError('Поля: неверный элемент')
        field = {'id': _str(str(raw.get('id') or i + 1), 'id поля', limit=40), 'label': _str(raw.get('label'), 'Подпись поля', required=False, limit=300)}
        if variant == 'inline_select':
            field['options'] = _strings(raw.get('options'), f'Варианты поля {i + 1}', min_len=2, max_len=30)
        fields.append(field)
    ids = [f['id'] for f in fields]
    if len(set(ids)) != len(ids):
        raise TaskError('повторяющиеся поля')
    if variant in ('single', 'number', 'formula') and len(fields) != 1:
        raise TaskError('в этом варианте одно поле')
    result = {'fields': fields}
    if variant in ('inline', 'inline_select'):
        text = _str(data.get('text'), 'Текст с пропусками')
        if set(FIELD_RE.findall(text)) != set(ids):
            raise TaskError('пропуски в тексте не совпадают с полями')
        result['text'] = text
    if variant == 'table':
        columns = _strings(data.get('columns'), 'Столбцы', min_len=1, max_len=12, limit=200)
        rows = []
        for r, row in enumerate(_list(data.get('rows'), 'Строки', min_len=1, max_len=40)):
            cells = _list(row, f'Строка {r + 1}', min_len=len(columns), max_len=len(columns))
            rows.append([_str(c, f'Ячейка {r + 1}', required=False, limit=300) for c in cells])
        used = {m for row in rows for c in row for m in FIELD_RE.findall(c)}
        if used != set(ids):
            raise TaskError('поля таблицы не совпадают с полями')
        result['columns'], result['rows'] = columns, rows
    if answer is not None:
        accepted = {}
        raw_fields = answer.get('fields') if isinstance(answer.get('fields'), dict) else {}
        for field_id in ids:
            values = raw_fields.get(field_id) or []
            values = [values] if isinstance(values, str) else values
            values = [v for v in _strings(values, f'Ответ поля {field_id}', min_len=0, max_len=20) if v]
            if variant == 'number':
                values = [str(_number(v, 'Числовой ответ')) for v in values]
            if variant == 'inline_select':
                options = next(f['options'] for f in fields if f['id'] == field_id)
                if any(v not in options for v in values):
                    raise TaskError('правильный ответ должен быть одним из вариантов')
            if values:
                accepted[field_id] = values
        if not accepted:
            answer = None
        elif set(accepted) != set(ids):
            raise TaskError('укажите правильный ответ для каждого поля или ни для одного')
        else:
            answer = {'fields': accepted, 'tolerance': abs(_number(answer.get('tolerance') or 0, 'Допуск'))}
    return result, answer


def _v_open(variant, data, answer):
    result = {'placeholder': _str(data.get('placeholder'), 'Подсказка', required=False, limit=300)}
    if variant == 'blocks':
        result['max_blocks'] = int(_number(data.get('max_blocks') or 5, 'Число блоков', minimum=1))
    if answer is not None:
        if variant == 'short':
            values = [v for v in _strings(answer.get('accepted') or [], 'Ответ', min_len=0, max_len=20) if v]
            answer = {'accepted': values} if values else None
        elif variant == 'number':
            value = answer.get('value')
            answer = None if value in (None, '') else {'value': _number(value, 'Ответ'), 'tolerance': abs(_number(answer.get('tolerance') or 0, 'Допуск'))}
        else:
            answer = None  # развёрнутые ответы проверяет преподаватель
    return result, answer


def _v_ordering(variant, data, answer):
    items = _items(data.get('items'), 'Элементы', min_len=2, max_len=40)
    # Правильный порядок — порядок, заданный преподавателем; ученик получает перемешанный.
    if answer is not None:
        answer = {'order': [i['id'] for i in items]} if answer.get('enabled', True) else None
    return {'items': items}, answer


def _v_categorize(variant, data, answer):
    min_cat, max_cat = {'two': (2, 2), 'many': (3, 20)}.get(variant, (2, 20))
    items = _items(data.get('items'), 'Элементы', min_len=1, max_len=60)
    categories = _items(data.get('categories'), 'Категории', min_len=min_cat, max_len=max_cat)
    if answer is not None:
        cat_ids = {c['id'] for c in categories}
        raw = answer.get('map') if isinstance(answer.get('map'), dict) else {}
        mapping = {}
        for item in items:
            cats = _ids(raw.get(item['id']) or [], 'Категории элемента', cat_ids)
            if variant != 'multi' and len(cats) > 1:
                raise TaskError('элемент относится только к одной категории')
            mapping[item['id']] = sorted(cats)
        answer = {'map': mapping} if any(mapping.values()) else None
    return {'items': items, 'categories': categories}, answer


def _v_selection(variant, data, answer):
    result = {'image': _url(data.get('image'))}
    if variant != 'position':
        result['elements'] = _items(data.get('elements'), 'Элементы', min_len=1, max_len=60, limit=200, extra=('x', 'y'))
    if variant == 'scheme':
        ids = {e['id'] for e in result['elements']}
        result['edges'] = _edges(data.get('edges') or [], ids, directed=True)
    if variant == 'place_labels':
        result['labels'] = _strings(data.get('labels'), 'Метки', min_len=1, max_len=60, limit=200)
    if answer is None:
        return result, None
    ids = {e['id'] for e in result.get('elements', [])}
    if variant in ('one', 'many', 'scheme'):
        selected = _ids(answer.get('selected') or [], 'Правильные элементы', ids)
        if variant == 'one' and len(selected) > 1:
            raise TaskError('отметьте один элемент')
        answer = {'selected': sorted(selected)} if selected else None
    elif variant == 'position':
        region = answer.get('region')
        if not isinstance(region, dict):
            return result, None
        answer = {'region': {k: _coord(region.get(k), f'Область.{k}') for k in ('x', 'y', 'w', 'h')}}
    elif variant == 'place_labels':
        raw = answer.get('map') if isinstance(answer.get('map'), dict) else {}
        mapping = {k: v for k, v in raw.items() if k in ids and v in result['labels']}
        answer = {'map': mapping} if mapping else None
    else:  # name
        raw = answer.get('names') if isinstance(answer.get('names'), dict) else {}
        names = {}
        for element_id in ids:
            values = raw.get(element_id) or []
            values = [values] if isinstance(values, str) else values
            values = [v for v in _strings(values, 'Подпись', min_len=0, max_len=10, limit=200) if v]
            if values:
                names[element_id] = values
        answer = {'names': names} if names else None
    return result, answer


def _url(value):
    value = _str(value, 'Изображение', required=False, limit=1000)
    if value and not re.match(r'^https?://', value, re.I):
        raise TaskError('ссылка на изображение должна начинаться с http:// или https://')
    return value


def _edges(value, ids, *, directed):
    edges = set()
    for edge in _list(value, 'Связи', max_len=400):
        if not (isinstance(edge, list) and len(edge) == 2 and edge[0] in ids and edge[1] in ids and edge[0] != edge[1]):
            raise TaskError('Связи: неверная связь')
        edges.add(tuple(edge) if directed else tuple(sorted(edge)))
    return sorted([list(e) for e in edges])


def _v_connecting(variant, data, answer):
    nodes = _items(data.get('nodes'), 'Узлы', min_len=2, max_len=40, limit=200, extra=('x', 'y'))
    result = {'nodes': nodes, 'directed': variant == 'directed'}
    if variant == 'single':
        result['max_edges'] = 1
    if answer is not None:
        edges = _edges(answer.get('edges') or [], {n['id'] for n in nodes}, directed=result['directed'])
        if variant == 'single' and len(edges) > 1:
            raise TaskError('в этом варианте одна связь')
        answer = {'edges': edges} if edges else None
    return result, answer


def _v_editing(variant, data, answer):
    if variant == 'reorder':
        lines = _items(data.get('lines'), 'Строки', min_len=2, max_len=40)
        if answer is not None:
            answer = {'order': [line['id'] for line in lines]} if answer.get('enabled', True) else None
        return {'lines': lines}, answer
    text = _str(data.get('text'), 'Исходный текст')
    result = {'text': text, 'tokens': tokens(text)}
    if answer is None:
        return result, None
    if variant in ('highlight', 'delete'):
        indices = _indices(answer.get('indices') or [], 'Отмеченные слова', len(result['tokens']))
        answer = {'indices': indices} if indices else None
    else:  # rewrite, replace, insert — сравнение с итоговым текстом
        target = _str(answer.get('text'), 'Исправленный текст', required=False)
        answer = {'text': target} if target else None
    return result, answer


VALIDATORS = {
    'choice': _v_choice, 'matching': _v_matching, 'fill': _v_fill, 'open': _v_open,
    'ordering': _v_ordering, 'categorize': _v_categorize, 'selection': _v_selection,
    'connecting': _v_connecting, 'editing': _v_editing,
}


# ---------- выдача ученику ----------

def for_student(task, seed):
    """Копия задания без правильных ответов; порядок, который сам является ответом, перемешан."""
    data = {k: (list(v) if isinstance(v, list) else v) for k, v in task['data'].items()}
    rnd = random.Random(f'{seed}:{task["id"]}')
    for key in ('items', 'lines') if task['kind'] in ('ordering', 'editing') else ():
        if key in data:
            original = list(data[key])
            for _ in range(5):
                rnd.shuffle(data[key])
                if data[key] != original:
                    break
    if task['kind'] == 'matching':
        rnd.shuffle(data['right'])
    if task['kind'] == 'selection' and 'labels' in data:
        rnd.shuffle(data['labels'])
    return {k: task[k] for k in ('id', 'kind', 'variant', 'prompt', 'points')} | {'data': data, 'graded': task['answer'] is not None}


# ---------- автопроверка ----------

def grade_task(task, given):
    """Возвращает {'status': correct|wrong|manual|empty, 'points': float}."""
    answer = task.get('answer')
    if answer is None or task['points'] <= 0:
        return {'status': 'manual' if _filled(given) else 'empty', 'points': 0.0}
    if not _filled(given):
        return {'status': 'empty', 'points': 0.0}
    try:
        ok = CHECKERS[task['kind']](task, answer, given)
    except (TypeError, ValueError, KeyError, AttributeError):
        ok = False
    return {'status': 'correct' if ok else 'wrong', 'points': task['points'] if ok else 0.0}


def _filled(given):
    if given in (None, '', [], {}):
        return False
    if isinstance(given, dict):
        return any(_filled(v) for v in given.values())
    return True


def _set_of_ints(values):
    return {int(v) for v in values}


def _c_choice(task, answer, given):
    return _set_of_ints(given.get('selected', [])) == set(answer['correct'])


def _c_matching(task, answer, given):
    return {tuple(p) for p in given.get('pairs', [])} == {tuple(p) for p in answer['pairs']}


def _c_fill(task, answer, given):
    values = given.get('fields', {})
    for field_id, accepted in answer['fields'].items():
        value = values.get(field_id)
        if task['variant'] == 'number':
            number = parse_number(value)
            if number is None or not any(abs(number - float(a)) <= answer.get('tolerance', 0) + 1e-9 for a in accepted):
                return False
        elif task['variant'] == 'formula':
            if norm_formula(value) not in {norm_formula(a) for a in accepted}:
                return False
        elif norm_text(value) not in {norm_text(a) for a in accepted}:
            return False
    return True


def _c_open(task, answer, given):
    if task['variant'] == 'number':
        number = parse_number(given.get('text'))
        return number is not None and abs(number - answer['value']) <= answer['tolerance'] + 1e-9
    return norm_text(given.get('text')) in {norm_text(a) for a in answer['accepted']}


def _c_order(task, answer, given):
    return [str(v) for v in given.get('order', [])] == answer['order']


def _c_categorize(task, answer, given):
    mapping = given.get('map', {})
    return all(sorted(mapping.get(item, []) or []) == cats for item, cats in answer['map'].items())


def _c_selection(task, answer, given):
    variant = task['variant']
    if variant in ('one', 'many', 'scheme'):
        return sorted(set(given.get('selected', []))) == answer['selected']
    if variant == 'position':
        point, region = given.get('point') or {}, answer['region']
        x, y = float(point['x']), float(point['y'])
        return region['x'] <= x <= region['x'] + region['w'] and region['y'] <= y <= region['y'] + region['h']
    if variant == 'place_labels':
        mapping = given.get('map', {})
        return all(mapping.get(k) == v for k, v in answer['map'].items())
    names = given.get('names', {})
    return all(norm_text(names.get(k)) in {norm_text(a) for a in v} for k, v in answer['names'].items())


def _c_connecting(task, answer, given):
    directed = task['data'].get('directed')
    edges = {tuple(e) if directed else tuple(sorted(e)) for e in given.get('edges', [])}
    return edges == {tuple(e) for e in answer['edges']}


def _c_editing(task, answer, given):
    variant = task['variant']
    words = list(task['data'].get('tokens', []))
    if variant == 'reorder':
        return [str(v) for v in given.get('order', [])] == answer['order']
    if variant in ('highlight', 'delete'):
        return sorted(_set_of_ints(given.get('indices', []))) == answer['indices']
    if variant == 'rewrite':
        result = given.get('text', '')
    elif variant == 'replace':
        replacements = given.get('replacements', {})
        result = ' '.join(str(replacements.get(str(i), w)) for i, w in enumerate(words))
    else:  # insert: вставка перед словом с номером gap (gap == len(words) — в конец)
        inserts = given.get('inserts', {})
        parts = []
        for i in range(len(words) + 1):
            if str(i) in inserts and str(inserts[str(i)]).strip():
                parts.append(str(inserts[str(i)]))
            if i < len(words):
                parts.append(words[i])
        result = ' '.join(parts)
    return norm_text(result) == norm_text(answer['text'])


CHECKERS = {
    'choice': _c_choice, 'matching': _c_matching, 'fill': _c_fill, 'open': _c_open,
    'ordering': _c_order, 'categorize': _c_categorize, 'selection': _c_selection,
    'connecting': _c_connecting, 'editing': _c_editing,
}


def auto_grade(score, max_score, good_percent, excellent_percent):
    """Оценка по шкале; минимум «удовлетворительно». Без автопроверяемых заданий — None."""
    if max_score <= 0:
        return None
    percent = score * 100 / max_score
    if percent >= excellent_percent:
        return GRADES[2]
    if percent >= good_percent:
        return GRADES[1]
    return GRADES[0]


def grade_attempt(tasks, answers):
    results, score, max_score = {}, 0.0, 0.0
    for task in tasks:
        result = grade_task(task, answers.get(task['id']))
        results[task['id']] = result
        score += result['points']
        if task['answer'] is not None:
            max_score += task['points']
    return results, round(score, 2), round(max_score, 2)
