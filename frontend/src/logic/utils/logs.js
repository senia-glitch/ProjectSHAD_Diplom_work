// Представление записей журнала: время, цвет уровня, компактный JSON.
// Чистые функции — страница только рисует.

export function formatLogTs(iso) {
  const d = new Date(String(iso ?? '').replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(iso ?? '')
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export function logLevelClass(lvl) {
  const key = String(lvl || '').toLowerCase()
  if (key === 'error') return 'lvl lvl--error'
  if (key === 'warn') return 'lvl lvl--warn'
  return 'lvl lvl--info'
}

// data в таблице — компактный JSON; длинное режется.
export function formatLogData(data, max = 120) {
  if (!data || typeof data !== 'object') return ''
  let json
  try {
    json = JSON.stringify(data)
  } catch {
    return ''
  }
  return json.length > max ? `${json.slice(0, max)}…` : json
}
