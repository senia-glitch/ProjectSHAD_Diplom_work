// Форматирование для страниц админ-панели (отображение, без данных и сети).

export const ACTION_LABELS = {
  login: 'Вход по ключу',
  login_failed: 'Неудачный вход',
  rotate_key: 'Новый ключ',
  block_user: 'Блокировка',
  unblock_user: 'Разблокировка',
  reset_password: 'Сброс пароля',
  delete_user: 'Удаление пользователя',
  db_update_row: 'Изменение строки',
  db_delete_row: 'Удаление строки',
  db_sql_read: 'SQL: чтение',
  db_sql_read_failed: 'SQL: ошибка чтения',
  db_sql_write: 'SQL: изменение',
  db_sql_write_failed: 'SQL: ошибка изменения',
}

// Сервер хранит время в UTC без пояса: показываем в часовом поясе браузера владельца.
export function formatLocalDateTime(value) {
  if (!value) return ''
  const text = String(value)
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : text + 'Z'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return text
  return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Значение ячейки таблицы БД для показа: объекты — JSON, длинное — обрезаем.
export function cellText(value, max = 120) {
  if (value === null || value === undefined) return 'NULL'
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
  return text.length > max ? text.slice(0, max) + '…' : text
}

// Значение для поля формы редактирования (null → пустая строка с отметкой NULL отдельно).
export function editText(value) {
  if (value === null || value === undefined) return ''
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
}
