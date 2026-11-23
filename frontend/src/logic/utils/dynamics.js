// Динамика статистики репетитора: таблица Год 12x31, недели ISO, отчёт.
// Чистые функции без состояния. Источник данных — детали уроков
// GET /tutor/lessons/details (один запрос за год), бэк не меняем.
//
// Определения (согласованы с заказчиком):
// - выручка = сумма ОПЛАЧЕННЫХ линий проведённых уроков;
// - время = часы проведённых уроков (минуты/60, 1 знак);
// - отмены в матрице — счётчик CANCELLED/NO_SHOW за день;
// - оплаченные/неоплаченные как метрики матрицы — заглушки (disabled в UI),
//   функции подсчёта реализованы и покрыты тестами на будущее.

export const DYN_METRICS = [
  { value: 'conducted', label: 'Проведённые' },
  { value: 'planned', label: 'Запланированные' },
  { value: 'revenue', label: 'Выручка' },
  { value: 'time', label: 'Время (ч)' },
  { value: 'cancelled', label: 'Отмены' },
  { value: 'paid', label: 'Оплаченные' },
  { value: 'unpaid', label: 'Неоплаченные' },
]

export const DYN_MODES = [
  { value: 'year', label: 'Год' },
  { value: 'week', label: 'Неделя' },
]

// Фильтры блока «Уроки»: чекбокс «Запланированные» покрывает
// SCHEDULED и ONGOING.
export const LESSON_STATUS_OPTIONS = [
  { value: 'FINISHED', label: 'Проведённые' },
  { value: 'SCHEDULED', label: 'Запланированные' },
  { value: 'CANCELLED', label: 'Отменённые' },
  { value: 'NO_SHOW', label: 'Неявки' },
]

export const LESSON_TYPE_OPTIONS = [
  { value: 'all', label: 'Все' },
  { value: 'single', label: 'Индивидуальные' },
  { value: 'group', label: 'Групповые' },
]

const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

export function monthShort(m) {
  return MONTHS_SHORT[m] || ''
}

export function daysInMonth(year, m) {
  return new Date(year, m + 1, 0).getDate()
}

export function isConducted(status) {
  return status === 'FINISHED'
}

export function isPlanned(status) {
  return status === 'SCHEDULED' || status === 'ONGOING'
}

export function isCancelled(status) {
  return status === 'CANCELLED' || status === 'NO_SHOW'
}

// Раскладка года: 12 строк x 31 ячейка. В ячейке — массив уроков дня
// (включая пустые). Несуществующие дни помечены exists:false.
export function pivotYear(lessons, year) {
  const grid = []
  const byDate = new Map()
  for (const l of lessons || []) {
    if (!l || typeof l.date !== 'string') continue
    if (!byDate.has(l.date)) byDate.set(l.date, [])
    byDate.get(l.date).push(l)
  }
  for (let m = 0; m < 12; m++) {
    const dim = daysInMonth(year, m)
    const row = []
    for (let d = 1; d <= 31; d++) {
      if (d > dim) {
        row.push({ exists: false, lessons: [] })
      } else {
        const iso = `${year}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
        row.push({ exists: true, date: iso, lessons: byDate.get(iso) || [] })
      }
    }
    grid.push(row)
  }
  return grid
}

function paidLinesSum(lesson) {
  return (lesson.students || []).reduce((s, x) => s + (x.paid ? x.amount || 0 : 0), 0)
}

function unpaidLinesSum(lesson) {
  return (lesson.students || []).reduce((s, x) => s + (!x.paid ? x.amount || 0 : 0), 0)
}

export function cellValue(dayLessons, metric) {
  const list = dayLessons || []
  switch (metric) {
    case 'conducted':
      return list.filter((l) => isConducted(l.status)).length
    case 'planned':
      return list.filter((l) => isPlanned(l.status)).length
    case 'cancelled':
      return list.filter((l) => isCancelled(l.status)).length
    case 'revenue':
      return list
        .filter((l) => isConducted(l.status))
        .reduce((s, l) => s + paidLinesSum(l), 0)
    case 'time': {
      const minutes = list
        .filter((l) => isConducted(l.status))
        .reduce((s, l) => s + (l.minutes || 0), 0)
      return Math.round((minutes / 60) * 10) / 10
    }
    case 'paid':
      return list
        .filter((l) => isConducted(l.status))
        .reduce((s, l) => s + paidLinesSum(l), 0)
    case 'unpaid':
      return list
        .filter((l) => isConducted(l.status))
        .reduce((s, l) => s + unpaidLinesSum(l), 0)
    default:
      return 0
  }
}

export function matrixMax(grid, metric) {
  let max = 0
  for (const row of grid || []) {
    for (const cell of row) {
      if (!cell.exists) continue
      const v = cellValue(cell.lessons, metric)
      if (v > max) max = v
    }
  }
  return max
}

// Шкала синего: 0 — не красим (ноль = пусто), 1..5 шагом 20% от max.
export function shadeLevel(value, max) {
  if (!(value > 0) || !(max > 0)) return 0
  return Math.min(5, Math.max(1, Math.ceil((value / max) * 5)))
}

function trim1(v) {
  const r = Math.round(v * 10) / 10
  return String(r).replace('.', ',')
}

export function fmtCompactRu(v) {
  const n = Math.round(v || 0)
  if (n < 1000) return String(n)
  if (n < 1_000_000) {
    const k = n / 1000
    const s = (Math.round(k * 10) / 10).toString().replace('.', ',')
    return `${s}к`
  }
  const m = n / 1_000_000
  return `${(Math.round(m * 10) / 10).toString().replace('.', ',')}М`
}

// Короткое числовое значение ячейки (без перегрузки таблицы).
export function fmtCellValue(value, metric) {
  if (!(value > 0)) return ''
  if (metric === 'time') return trim1(value)
  if (metric === 'revenue' || metric === 'paid' || metric === 'unpaid') return fmtCompactRu(value)
  return String(Math.round(value))
}

function toISODateLocal(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function mondayOfDate(d) {
  const x = new Date(d.getTime())
  const shift = (x.getDay() + 6) % 7
  x.setDate(x.getDate() - shift)
  return x
}

function isoWeekNumber(d) {
  // ISO: номер недели = неделя четверга.
  const thu = new Date(d.getTime())
  thu.setDate(thu.getDate() + (3 - ((d.getDay() + 6) % 7)))
  const jan4 = new Date(thu.getFullYear(), 0, 4)
  const jan4Mon = mondayOfDate(jan4)
  return 1 + Math.round((mondayOfDate(thu).getTime() - jan4Mon.getTime()) / (7 * 86400000))
}

export function fmtShortRange(fromIso, toIso) {
  const f = (iso) => `${iso.slice(8, 10)}.${iso.slice(5, 7)}`
  return `${f(fromIso)}–${f(toIso)}`
}

// Недели ISO Пн–Вс, пересекающие год. Карточка может лежать
// в двух месяцах (fromM..toM) — это одна сущность.
export function isoWeeksOfYear(year) {
  const jan1 = new Date(year, 0, 1, 12, 0, 0)
  let mon = mondayOfDate(jan1)
  const end = new Date(year, 11, 31, 12, 0, 0)
  const out = []
  while (mon <= end) {
    const sun = new Date(mon.getTime())
    sun.setDate(sun.getDate() + 6)
    const from = toISODateLocal(mon)
    const to = toISODateLocal(sun)
    out.push({
      key: `${from}_${to}`,
      week: isoWeekNumber(mon),
      from,
      to,
      fromM: mon.getMonth(),
      toM: sun.getMonth(),
      fromY: mon.getFullYear(),
      toY: sun.getFullYear(),
    })
    mon = new Date(mon.getTime())
    mon.setDate(mon.getDate() + 7)
  }
  return out
}

// Колонки карточки недели в сетке 12 месяцев года.
// Неделя через стык лет обрезается по году: часть вне года не рисуем.
export function weekSpan(year, w) {
  const start = w.fromY === year ? w.fromM + 1 : 1
  const end = w.toY === year ? w.toM + 1 : 12
  const s = Math.min(start, end)
  const e = Math.max(start, end)
  return { start: s, span: e - s + 1 }
}

// Строки-записи (линии ученик-урок) в диапазоне, хронологически.
// Под «уроком» в списке понимается запись: цена/оплата из записи,
// дата/статус — из урока.
export function linesInRange(lessons, fromIso, toIso) {
  const rows = []
  for (const l of lessons || []) {
    if (!l || typeof l.date !== 'string') continue
    if (l.date < fromIso || l.date > toIso) continue
    for (const s of l.students || []) {
      rows.push({
        lesson_id: l.lesson_id,
        date: l.date,
        start: l.start || '',
        end: l.end || '',
        minutes: l.minutes || 0,
        is_group: Boolean(l.is_group),
        status: l.status,
        student_id: s.student_id,
        student_user_id: s.student_user_id,
        name: s.student_name || s.name || '',
        amount: s.amount || 0,
        paid: Boolean(s.paid),
        links: l.links || [],
        descriptions: l.lesson_descriptions || l.descriptions || '',
      })
    }
  }
  rows.sort((a, b) => (
    a.date < b.date ? -1 : a.date > b.date ? 1
    : a.start < b.start ? -1 : a.start > b.start ? 1
    : String(a.name).localeCompare(String(b.name), 'ru')
  ))
  return rows
}

export function lineGroup(status) {
  if (isConducted(status)) return 'conducted'
  if (isPlanned(status)) return 'planned'
  if (isCancelled(status)) return 'cancelled'
  return 'other'
}

// Гибкое «что включаем»: группа статуса И группа оплаты должны совпасть.
export function filterLines(rows, include) {
  const inc = { conducted: true, planned: true, cancelled: true, paid: true, unpaid: true, ...(include || {}) }
  return (rows || []).filter((r) => {
    const g = lineGroup(r.status)
    if (g === 'conducted' && !inc.conducted) return false
    if (g === 'planned' && !inc.planned) return false
    if (g === 'cancelled' && !inc.cancelled) return false
    if (g === 'other') return false
    if (r.paid && !inc.paid) return false
    if (!r.paid && !inc.unpaid) return false
    return true
  })
}

function sumMinutes(lessons) {
  return (lessons || []).reduce((s, l) => s + (l.minutes || 0), 0)
}

function round1(v) {
  return Math.round(v * 10) / 10
}

// Агрегат отчёта по строкам-записям и урокам диапазона.
// periodDays — календарных дней в периоде (целое кольца времени).
// cancelCounts — {byStudent, byTutor} из details (сами записи details прячет).
export function aggregateReport(reportLessons, reportLines, periodDays, cancelCounts = null) {
  const lessons = reportLessons || []
  const lines = reportLines || []
  const conducted = lessons.filter((l) => isConducted(l.status))
  const planned = lessons.filter((l) => isPlanned(l.status))
  const cancelled = lessons.filter((l) => isCancelled(l.status))

  const cLines = lines.filter((r) => isConducted(r.status))
  const pLines = lines.filter((r) => isPlanned(r.status))
  const cPaid = cLines.filter((r) => r.paid)
  const cUnpaid = cLines.filter((r) => !r.paid)
  const pPaid = pLines.filter((r) => r.paid)
  const pUnpaid = pLines.filter((r) => !r.paid)

  const revenue = cPaid.reduce((s, r) => s + (r.amount || 0), 0)
  const plannedPotential = planned.reduce((s, l) => s + (l.total || 0), 0)
  const anySum = lessons.reduce((s, l) => s + (l.total || 0), 0)

  const conductedH = round1(sumMinutes(conducted) / 60)
  const plannedH = round1(sumMinutes(planned) / 60)
  const periodH = Math.max(0, (periodDays || 0) * 24)
  const freeH = round1(Math.max(0, periodH - conductedH - plannedH))

  // Время делим по урокам, а не по линиям: минуты урока распределяются
  // пропорционально доле оплаченных записей (иначе группа из N учеников
  // умножала бы часы в N раз и сплиты не сходились бы с сегментом).
  // Урок без записей — всё время в неоплаченные (денег не поступило).
  const splitH = (ls) => {
    let paid = 0
    let unpaid = 0
    for (const l of ls) {
      const total = (l.students || []).length
      const paidCount = (l.students || []).filter((s) => s.paid).length
      const frac = total > 0 ? paidCount / total : 0
      paid += (l.minutes || 0) * frac
      unpaid += (l.minutes || 0) * (1 - frac)
    }
    return { paid: round1(paid / 60), unpaid: round1(unpaid / 60) }
  }
  const cSplit = splitH(conducted)
  const pSplit = splitH(planned)

  return {
    finance: {
      revenue,
      avgPaid: cPaid.length ? Math.round(revenue / cPaid.length) : 0,
      avgPaidCount: cPaid.length,
      avgPlanned: planned.length ? Math.round(plannedPotential / planned.length) : 0,
      avgPlannedCount: planned.length,
      avgAny: lessons.length ? Math.round(anySum / lessons.length) : 0,
      avgAnyCount: lessons.length,
      avgDurConducted: conducted.length ? round1(sumMinutes(conducted) / conducted.length) : 0,
      avgDurPlanned: planned.length ? round1(sumMinutes(planned) / planned.length) : 0,
      avgDurAny: lessons.length ? round1(sumMinutes(lessons) / lessons.length) : 0,
    },
    lessonsDonut: {
      conducted: conducted.length,
      conductedPaid: cPaid.length,
      conductedUnpaid: cUnpaid.length,
      planned: planned.length,
      plannedPaid: pPaid.length,
      plannedUnpaid: pUnpaid.length,
      cancelled: cancelled.length,
      cancelledByStudent: cancelCounts?.byStudent || 0,
      cancelledByTutor: cancelCounts?.byTutor || 0,
    },
    timeDonut: {
      conductedH,
      conductedPaidH: cSplit.paid,
      conductedUnpaidH: cSplit.unpaid,
      plannedH,
      plannedPaidH: pSplit.paid,
      plannedUnpaidH: pSplit.unpaid,
      freeH,
      periodH,
    },
  }
}

export function daysBetweenInclusive(fromIso, toIso) {
  if (!fromIso || !toIso || toIso < fromIso) return 0
  const a = new Date(`${fromIso}T12:00:00`).getTime()
  const b = new Date(`${toIso}T12:00:00`).getTime()
  return Math.round((b - a) / 86400000) + 1
}

// Ряд ученика на полной сетке бакетов периода: недостающие бакеты — нули.
// Чинит «сен–окт при фильтре год»: сырой by_student_series разрежен
// (только бакеты с уроками), а series — полный.
export function alignSeries(buckets, cells) {
  const byBucket = new Map((cells || []).map((c) => [c.bucket, c]))
  return (buckets || []).map((b) => {
    const c = byBucket.get(b)
    return { bucket: b, revenue: c?.revenue || 0, forecast: c?.forecast || 0 }
  })
}

// CSV отчёта: ровно содержимое настроенного отчёта (без поля выбора).
export function reportToCsv({ title, rangeLabel, agg, rows, showLinks }) {
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = []
  const row = (cells) => lines.push(cells.map(esc).join(';'))
  row(['Отчёт', title || ''])
  row(['Период', rangeLabel || ''])
  lines.push('')
  row(['ФИНАНСЫ'])
  row(['Показатель', 'Значение'])
  const f = agg?.finance || {}
  for (const [k, v] of [
    ['Выручка (проведённые оплаченные)', f.revenue || 0],
    ['Средняя цена по выручке', f.avgPaid || 0],
    ['Оплаченных линий', f.avgPaidCount || 0],
    ['Средняя цена запланированных', f.avgPlanned || 0],
    ['Запланированных уроков', f.avgPlannedCount || 0],
    ['Средняя цена любых', f.avgAny || 0],
    ['Уроков всего', f.avgAnyCount || 0],
    ['Средняя длительность проведённых, мин', f.avgDurConducted || 0],
    ['Средняя длительность запланированных, мин', f.avgDurPlanned || 0],
    ['Средняя длительность любых, мин', f.avgDurAny || 0],
  ]) row([k, v])
  lines.push('')
  row(['УРОКИ'])
  const d = agg?.lessonsDonut || {}
  for (const [k, v] of [
    ['Проведённые', d.conducted || 0],
    ['Проведённые оплаченные (линии)', d.conductedPaid || 0],
    ['Проведённые неоплаченные (линии)', d.conductedUnpaid || 0],
    ['Запланированные', d.planned || 0],
    ['Запланированные оплаченные (линии)', d.plannedPaid || 0],
    ['Запланированные неоплаченные (линии)', d.plannedUnpaid || 0],
    ['Отмены', d.cancelled || 0],
    ['Отмены записей учеником', d.cancelledByStudent || 0],
    ['Отмены записей репетитором', d.cancelledByTutor || 0],
  ]) row([k, v])
  lines.push('')
  row(['ВРЕМЯ, ч'])
  const t = agg?.timeDonut || {}
  for (const [k, v] of [
    ['Проведено', t.conductedH || 0],
    ['Проведено оплаченные', t.conductedPaidH || 0],
    ['Проведено неоплаченные', t.conductedUnpaidH || 0],
    ['Запланировано', t.plannedH || 0],
    ['Запланировано оплаченные', t.plannedPaidH || 0],
    ['Запланировано неоплаченные', t.plannedUnpaidH || 0],
    ['Незанятое', t.freeH || 0],
    ['Период всего', t.periodH || 0],
  ]) row([k, v])
  lines.push('')
  row(['СПИСОК'])
  const head = ['Дата', 'Время', 'Ученик', 'Минут', 'Тип', 'Статус', 'Сумма', 'Оплата']
  if (showLinks) head.push('Ссылки')
  row(head)
  for (const r of rows || []) {
    const cells = [
      r.date, `${r.start}-${r.end}`, r.name, r.minutes,
      r.is_group ? 'групповой' : 'индивидуальный',
      r.status, r.amount, r.paid ? 'да' : '',
    ]
    if (showLinks) cells.push((r.links || []).map((x) => x.url || x.alias || '').filter(Boolean).join(' '))
    row(cells)
  }
  return '﻿' + lines.join('\r\n')

}
