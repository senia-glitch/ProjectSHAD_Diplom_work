// «Ближайшие уроки»: отбор и группировка (время — пояс пользователя, наивные строки).
// Без состояния, без сети, без DOM.

const ACTIVE = new Set(['PENDING', 'SCHEDULED', 'ONGOING'])
const HISTORY = new Set(['CANCELLED', 'REJECTED', 'SYSTEM_FINISHED'])

const pad = (n) => String(n).padStart(2, '0')

function addDays(dateIso, days) {
  const [y, m, d] = dateIso.slice(0, 10).split('-').map(Number)
  const t = new Date(Date.UTC(y, m - 1, d + days))
  return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}`
}

// Период загрузки: месяц истории отмен и неделя вперёд от сегодня пользователя.
export function upcomingRange(nowIso, { daysAhead = 7, historyDays = 30 } = {}) {
  const today = nowIso.slice(0, 10)
  return { dateFrom: addDays(today, -historyDays), dateTo: addDays(today, daysAhead) }
}

const WEEKDAY = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
const MONTH = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

function dayLabel(date, today) {
  if (date === today) return 'Сегодня'
  if (date === addDays(today, 1)) return 'Завтра'
  const [y, m, d] = date.split('-').map(Number)
  const wd = new Date(Date.UTC(y, m - 1, d)).getUTCDay()
  return `${d} ${MONTH[m - 1]}, ${WEEKDAY[wd]}`
}

// Активные уроки, ещё не закончившиеся, на daysAhead дней вперёд — по дням;
// история: отменённые/отклонённые/закрытые системой за historyDays дней, новые сверху.
export function groupUpcoming(lessons, nowIso, { daysAhead = 7, historyDays = 30 } = {}) {
  const today = nowIso.slice(0, 10)
  const until = `${addDays(today, daysAhead)}T23:59:59`
  const since = `${addDays(today, -historyDays)}T00:00:00`
  const active = (lessons || [])
    .filter((l) => ACTIVE.has(l.status) && l.end_time > nowIso && l.start_time <= until)
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
  const days = []
  for (const lesson of active) {
    const date = lesson.start_time.slice(0, 10)
    let day = days[days.length - 1]
    if (!day || day.date !== date) {
      day = { date, label: dayLabel(date, today), lessons: [] }
      days.push(day)
    }
    day.lessons.push(lesson)
  }
  const history = (lessons || [])
    .filter((l) => HISTORY.has(l.status) && l.start_time >= since)
    .sort((a, b) => b.start_time.localeCompare(a.start_time))
  return { days, history, pendingCount: active.filter((l) => l.status === 'PENDING').length }
}
