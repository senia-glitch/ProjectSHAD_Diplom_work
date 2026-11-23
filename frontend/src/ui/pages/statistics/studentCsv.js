// Выгрузки по ученику и хронологии: чистые построители CSV.
// Имена файлов: statistika_{тип}_{период}_{ученик}.csv
import { csvEsc } from '../../../logic/utils/index.js'

export function reportFileName(type, period, studentId = null) {
  const safe = (s) => String(s || 'period').replace(/[^0-9A-Za-z_-]/g, '')
  return `statistika_${type}_${safe(period)}${studentId != null ? `_${studentId}` : ''}.csv`
}

const ESC = String.fromCharCode(65279)
function withBom(text) {
  return ESC + text
}

// Кратко по ученику: одна строка итогов.
export function studentBriefCsv(row) {
  const head = ['Ученик', 'Уроки', 'Часы', 'Выручка', 'Средний чек', 'Отмены', 'Неявки',
    'Прогноз уроков', 'Прогноз выручка', 'Первая встреча', 'Последняя встреча']
  const avg = row.lessons ? Math.round(row.revenue / row.lessons) : 0
  const body = [[
    row.student_name, row.lessons, row.billed_hours, row.revenue, avg,
    row.cancelled, row.no_show, row.forecast_lessons, row.forecast_revenue,
    row.first_lesson || '', row.last_lesson || '',
  ]]
  const lines = [head, ...body].map((r) => r.map(csvEsc).join(';'))
  return withBom(lines.join('\r\n'))
}

// Подробно по ученику: каждый урок.
export function studentDetailedCsv(lessons, studentId) {
  const head = ['Дата', 'Время', 'Минут', 'Тип', 'Статус', 'Сумма', 'Оценочно', 'Заметки', 'Ссылки']
  const body = (lessons || [])
    .filter((l) => (l.students || []).some((s) => s.student_id === studentId))
    .map((l) => {
      const me = l.students.find((s) => s.student_id === studentId)
      return [
        l.date, `${l.start}-${l.end}`, l.minutes,
        l.is_group ? 'групповой' : 'индивидуальный', l.status,
        me.amount, me.estimated ? 'да' : '',
        l.descriptions || '',
        (l.links || []).map((x) => x.url || x.alias || '').filter(Boolean).join(' '),
      ]
    })
  return withBom([head.map(csvEsc).join(';'), ...body.map((r) => r.map(csvEsc).join(';'))].join('\r\n'))
}

// Таблица «По ученикам» как на экране: видимые строки + долг.
// debtById: { student_id: сумма неоплаченных проведённых }.
export function studentsTableToCsv(rows, debtById) {
  const head = ['Ученик', 'Уроки', 'Часы', 'Выручка', 'Отмены', 'Неявки',
    'Прогноз', 'Средний чек', 'Статус', 'Долг']
  const body = (rows || []).map((r) => [
    r.student_name, r.lessons, r.billed_hours, r.revenue,
    r.cancelled, r.no_show, r.forecast_revenue,
    r.lessons ? Math.round(r.revenue / r.lessons) : 0,
    r.statusText || '', (debtById || {})[r.student_id] || 0,
  ])
  const lines = [head, ...body].map((x) => x.map(csvEsc).join(';'))
  return withBom(lines.join('\r\n'))
}

// Хронология уроков с учётом фильтров.
export function lessonsCsv(lessons) {
  const head = ['Дата', 'Время', 'Минут', 'Ученики', 'Тип', 'Статус', 'Сумма', 'Заметки']
  const body = (lessons || []).map((l) => [
    l.date, `${l.start}-${l.end}`, l.minutes,
    (l.students || []).map((s) => s.student_name).join(', '),
    l.is_group ? 'групповой' : 'индивидуальный', l.status, l.total,
    l.descriptions || '',
  ])
  return withBom([head.map(csvEsc).join(';'), ...body.map((r) => r.map(csvEsc).join(';'))].join('\r\n'))
}

export function downloadText(filename, text, mime = 'text/csv;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
