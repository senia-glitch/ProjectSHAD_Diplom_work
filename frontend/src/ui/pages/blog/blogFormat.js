// Форматирование для страниц блога (отображение, без данных и сети).
export function initials(name) {
  return (name || '?').trim().slice(0, 1).toUpperCase() || '?'
}

export function formatDate(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
  } catch {
    return ''
  }
}

export function formatDateTime(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function commentsWord(n) {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return 'комментарий'
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'комментария'
  return 'комментариев'
}
