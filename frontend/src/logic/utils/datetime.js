// Чистые функции дат/времени. Без состояния, без сети, без DOM.
export function toDateStr(iso) {
  if (!iso) return ''
  return iso.includes('T') ? iso.split('T')[0] : iso.split(' ')[0]
}

export function toMinutes(iso) {
  const t = iso?.includes('T') ? iso.split('T')[1] : iso?.split(' ')[1] || '00:00:00'
  const [h, m] = t.slice(0, 5).split(':').map(Number)
  return h * 60 + m
}

export function toMin(t) {
  const [h, m] = String(t).split(':').map(Number)
  return h * 60 + m
}

export function fmtTime(iso) {
  if (!iso) return ''
  const t = iso.includes('T') ? iso.split('T')[1] : iso.split(' ')[1]
  return t ? t.slice(0, 5) : iso
}

export function fmtDateTime(iso) {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 16)
}

export function fmtDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function toIso(value) {
  if (typeof value === 'string') return value.replace(' ', 'T')
  if (value && typeof value.isoformat === 'function') return value.isoformat()
  if (value instanceof Date) return value.toISOString()
  return String(value)
}

export function getWeekStart(date) {
  const d = new Date(date)
  const day = d.getDay()
  d.setDate(d.getDate() - day + (day === 0 ? -6 : 1))
  d.setHours(0, 0, 0, 0)
  return d
}

export function dateOf(value) {
  if (typeof value === 'string') return value.slice(0, 10)
  if (value instanceof Date) return fmtDate(value)
  if (value && typeof value.date === 'function') return fmtDate(value.date())
  return String(value).slice(0, 10)
}

// Ближайшее вхождение дня недели (JS getDay) от даты, включая её саму.
// Человек думает «начать с 23.09», система понимает «отсчёт от недели 23.09».
export function nearestWeekday(jsDay, from = new Date()) {
  const t = new Date(from)
  t.setHours(0, 0, 0, 0)
  const d = new Date(t)
  d.setDate(d.getDate() + ((jsDay - d.getDay() + 7) % 7))
  return fmtDate(d)
}
