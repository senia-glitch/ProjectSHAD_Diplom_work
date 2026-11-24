// Личный часовой пояс пользователя на границе API.
// Сервер хранит и отдаёт время только в UTC (наивные ISO-строки). Пользователь видит
// и вводит «стенное» время своего пояса (смещение в часах из его настроек).
// Перевод — только здесь, на границе api/*; остальной код работает в поясе пользователя.
// Арифметика через Date.UTC: результат не зависит от пояса браузера.

let offsetProvider = () => 0

export function registerOffsetProvider(fn) {
  offsetProvider = typeof fn === 'function' ? fn : () => 0
}

export function currentOffset() {
  const value = Number(offsetProvider())
  return Number.isFinite(value) ? value : 0
}

const NAIVE = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/

const pad = (n) => String(n).padStart(2, '0')

// Сдвиг наивной ISO-строки на hours часов. Не-время возвращается как есть.
export function shiftIso(iso, hours) {
  if (typeof iso !== 'string') return iso
  const m = NAIVE.exec(iso)
  if (!m || !hours) return m ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6] || '00'}` : iso
  const t = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) + hours * 3600000
  const d = new Date(t)
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`
}

// UTC с сервера → время пользователя.
export function toUserTime(iso, offset = currentOffset()) {
  return shiftIso(iso, offset)
}

// Время пользователя → UTC для сервера.
export function toServerTime(iso, offset = currentOffset()) {
  return shiftIso(iso, -offset)
}

function nextDay(date) {
  const [y, mo, d] = date.split('-').map(Number)
  const t = new Date(Date.UTC(y, mo - 1, d + 1))
  return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}`
}

// Период местных дат [dateFrom, dateTo] включительно → полуоткрытые UTC-границы.
export function rangeToServer(dateFrom, dateTo, offset = currentOffset()) {
  if (!dateFrom || !dateTo) return { dateFrom, dateTo }
  return {
    dateFrom: toServerTime(`${dateFrom}T00:00:00`, offset),
    dateTo: toServerTime(`${nextDay(dateTo)}T00:00:00`, offset),
  }
}

function mapNote(note, offset) {
  if (!note || typeof note !== 'object') return note
  return { ...note, at: toUserTime(note.at, offset) }
}

// Урок из ответа сервера → время пользователя (сам урок, пометки, история, дедлайн).
export function lessonToUser(lesson, offset = currentOffset()) {
  if (!lesson || typeof lesson !== 'object') return lesson
  const out = { ...lesson }
  for (const key of ['start_time', 'end_time', 'cancel_deadline']) {
    if (out[key]) out[key] = toUserTime(out[key], offset)
  }
  if (out.status_note) out.status_note = mapNote(out.status_note, offset)
  if (Array.isArray(out.status_history)) out.status_history = out.status_history.map((e) => mapNote(e, offset))
  if (out.absence) {
    out.absence = { ...out.absence, from: toUserTime(out.absence.from, offset), to: toUserTime(out.absence.to, offset) }
  }
  if (Array.isArray(out.students)) {
    out.students = out.students.map((s) => (s.cancelled_at ? { ...s, cancelled_at: toUserTime(s.cancelled_at, offset) } : s))
  }
  return out
}

export function absenceToUser(obj, offset = currentOffset()) {
  if (!obj) return obj
  return { ...obj, from: toUserTime(obj.from, offset), to: toUserTime(obj.to, offset) }
}

// «Сейчас» в поясе пользователя как Date, чьи местные поля — его стенное время.
// Так сравнения с наивными строками уроков (new Date('YYYY-MM-DDTHH:MM')) верны
// и тогда, когда пояс в настройках не совпадает с поясом браузера.
export function userNowIso(offset = currentOffset()) {
  return toUserTime(new Date().toISOString().slice(0, 19), offset)
}

export function userNowDate(offset = currentOffset()) {
  return new Date(userNowIso(offset))
}

export function userNowMs(offset = currentOffset()) {
  return userNowDate(offset).getTime()
}
