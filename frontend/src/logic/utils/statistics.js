// Форматирование чисел статистики. Чистые функции без состояния.
const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

export function formatMoney(value) {
  return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value || 0)} ₽`
}

export function formatHours(value) {
  return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(value || 0)} ч`
}

export function bucketLabel(bucket, granularity) {
  if (!bucket) return ''
  if (granularity === 'month') {
    const m = Number(bucket.slice(5, 7))
    return MONTHS_SHORT[m - 1] || bucket
  }
  if (granularity === 'week') {
    return `нед.${bucket.split('-W')[1] || bucket}`
  }
  return bucket.slice(8, 10) + '.' + bucket.slice(5, 7)
}

// Корзина относится к прогнозу, если начинается строго после сегодня.
// Сравнение строк ISO-дат корректно без парсинга.
export function isFutureBucket(bucketStartIso, todayIso) {
  return bucketStartIso > todayIso
}

function dayNum(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d) / 86400000
}

// Полных дней между датами ISO (YYYY-MM-DD).
export function daysSince(fromIso, todayIso) {
  if (!fromIso || !todayIso) return 0
  return Math.round(dayNum(todayIso) - dayNum(fromIso))
}

// Календарные проекции периода. Все принимают и отдают ISO-строки,
// мусор корректно превращается в null вместо исключения.
export function toISODate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function mondayOfIso(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return null
  const d = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(d.getTime())) return null
  const shift = (d.getDay() + 6) % 7
  d.setDate(d.getDate() - shift)
  return toISODateLocal(d)
}

export function addDaysIso(iso, n) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return null
  const d = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(d.getTime())) return null
  d.setDate(d.getDate() + n)
  return toISODateLocal(d)
}

export function monthRangeOf(monthStr) {
  if (!/^\d{4}-\d{2}$/.test(monthStr || '')) return null
  const [y, m] = monthStr.split('-').map(Number)
  if (m < 1 || m > 12) return null
  const last = new Date(y, m, 0).getDate()
  const pad = String(m).padStart(2, '0')
  return [`${y}-${pad}-01`, `${y}-${pad}-${last}`]
}

function toISODateLocal(d) {
  return toISODate(d)
}

// Единая точка правды: из сырого состояния фильтра — валидный диапазон
// и год, которому он принадлежит. Год выводится из дат, а не наоборот:
// иначе пресет «неделя» с якорем из другого года давал бы 422 и мёртвую страницу.
export function resolveRequestRange(f) {
  const fallbackYear = (y) => (Number.isInteger(y) && y >= 2000 && y <= 2100 ? y : new Date().getFullYear())
  let from = null
  let to = null
  if (f.preset === 'month') {
    const r = monthRangeOf(f.month)
    if (r) [from, to] = r
  } else if (f.preset === 'week') {
    const mon = mondayOfIso(f.weekAnchor)
    if (mon) {
      from = mon
      to = addDaysIso(mon, 6)
    }
  } else if (f.preset === 'custom') {
    const a = /^\d{4}-\d{2}-\d{2}$/.test(f.customFrom || '') ? f.customFrom : null
    const b = /^\d{4}-\d{2}-\d{2}$/.test(f.customTo || '') ? f.customTo : null
    if (a && b) [from, to] = a <= b ? [a, b] : [b, a]
  }
  if (!from || !to) {
    const y = fallbackYear(f.year)
    from = `${y}-01-01`
    to = `${y}-12-31`
  }
  return { year: Number(from.slice(0, 4)), dateFrom: from, dateTo: to }
}

// Сдвиг диапазона назад на его же длину: для сравнения с прошлым периодом.
export function shiftRange(fromIso, toIso) {
  const day = 86400000
  const d = (iso) => new Date(`${iso}T12:00:00`).getTime()
  const span = Math.round((d(toIso) - d(fromIso)) / day)
  const fmt = (t) => {
    const x = new Date(t)
    return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`
  }
  const prevTo = d(fromIso) - day
  return [fmt(prevTo - span * day), fmt(prevTo)]
}

// Ученик новый, если его первая встреча — внутри выбранного периода.
export function isNewStudent(firstLessonIso, rangeFromIso) {
  return Boolean(firstLessonIso && rangeFromIso) && firstLessonIso >= rangeFromIso
}

// Ученик неактивен, если он не новый в периоде и пауза дольше порога (дней).
export function isInactiveStudent(lastLessonIso, todayIso, isNew, thresholdDays = 30) {
  if (isNew || !lastLessonIso || !todayIso) return false
  return daysSince(lastLessonIso, todayIso) > thresholdDays
}

const PERIOD_WORD = { day: 'день', week: 'неделя', month: 'месяц' }

// Автовыводы по данным периода: дельта, лучший отрезок, новички,
// молчуны, занятость. Максимум 4, самые важные первые.
export function buildInsights(data, prevTotals, todayIso) {
  if (!data) return []
  const { totals, series, by_student, capacity, meta } = data
  const out = []
  if (prevTotals && prevTotals.revenue > 0) {
    const pct = Math.round(((totals.revenue - prevTotals.revenue) / prevTotals.revenue) * 100)
    out.push({
      tone: pct >= 0 ? 'good' : 'warn',
      text: `К прошлому периоду: ${pct >= 0 ? '+' : ''}${pct}%`,
    })
  }
  const best = (series || [])
    .filter((r) => r.lessons > 0)
    .sort((a, b) => b.revenue - a.revenue)[0]
  if (best) {
    out.push({
      tone: 'info',
      text: `Лучший ${PERIOD_WORD[meta.granularity] || 'период'} —`
        + ` ${bucketLabel(best.bucket, meta.granularity)}: ${formatMoney(best.revenue)}`,
    })
  }
  const fresh = (by_student || []).filter((r) => isNewStudent(r.first_lesson, meta.date_from))
  if (fresh.length) {
    const names = fresh.slice(0, 3).map((r) => r.student_name).join(', ')
    out.push({
      tone: 'good',
      text: `Новые${fresh.length > 1 ? ` (${fresh.length})` : ''}: ${names}${fresh.length > 3 ? ' и др.' : ''}`,
    })
  }
  const silent = (by_student || []).filter((r) =>
    isInactiveStudent(r.last_lesson, todayIso, isNewStudent(r.first_lesson, meta.date_from)))
  if (silent.length) {
    const names = silent.slice(0, 2).map((r) => r.student_name).join(', ')
    out.push({
      tone: 'warn',
      text: `Без занятий больше месяца${silent.length > 2 ? ` (${silent.length})` : ''}: ${names}${silent.length > 2 ? ' и др.' : ''}`,
    })
  }
  if (capacity && capacity.occupancy_pct != null) {
    out.push({ tone: 'info', text: `Занятость открытых часов ≈${capacity.occupancy_pct}%` })
  }
  return out.slice(0, 4)
}

// Диапазон ISO-недели «ГГГГ-WНН»: понедельник → воскресенье.
export function isoWeekRange(weekKey) {
  const [yStr, wStr] = weekKey.split('-W')
  const year = Number(yStr)
  const week = Number(wStr)
  const jan4 = new Date(Date.UTC(year, 0, 4))
  const monday = new Date(jan4.getTime() - ((jan4.getUTCDay() + 6) % 7) * 86400000 + (week - 1) * 7 * 86400000)
  const fmt = (t) => {
    const d = new Date(t)
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`
  }
  return [fmt(monday.getTime()), fmt(monday.getTime() + 6 * 86400000)]
}

// Ячейка CSV: экранирование кавычек, разделитель — снаружи.
export function csvEsc(v) {
  return `"${String(v ?? '').replace(/"/g, '""')}"`
}

// Таблица учеников → CSV (с BOM для Excel). Режим решает колонку денег.
export function studentsToCsv(rows, mode) {
  const money = (r) => (mode === 'fact' ? r.revenue : r.forecast_revenue)
  const lessons = (r) => (mode === 'fact' ? r.lessons : r.forecast_lessons)
  const head = mode === 'fact'
    ? ['Ученик', 'Уроки', 'Часы', 'Выручка', 'Отмены', 'Неявки']
    : ['Ученик', 'Уроков (план)', 'Прогноз']
  const body = (rows || []).map((r) => (mode === 'fact'
    ? [r.student_name, lessons(r), r.billed_hours, money(r), r.cancelled, r.no_show]
    : [r.student_name, lessons(r), money(r)]).map(csvEsc).join(';'))
  return '\uFEFF' + [head.map(csvEsc).join(';'), ...body].join('\r\n')
}

// Разделы полного отчёта. Порядок — как на странице.
export const REPORT_SECTIONS = [
  { key: 'summary', label: 'Сводка' },
  { key: 'series', label: 'Динамика' },
  { key: 'students', label: 'Ученики' },
  { key: 'weekday', label: 'Дни недели' },
  { key: 'hours', label: 'Часы' },
  { key: 'upcoming', label: 'Прогноз занятий' },
]

export function defaultReportOptions() {
  return { summary: true, series: true, students: true, weekday: true, hours: true, upcoming: true }
}

const WEEKDAYS_FULL = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

// Полный отчёт по ответу статистики: секции с заголовками, сырые числа
// (без форматирования с пробелами — чтобы Excel считал).
export function buildReport(data, options = defaultReportOptions(), nowIso = new Date().toISOString()) {
  const lines = []
  const row = (cells) => lines.push(cells.map(csvEsc).join(';'))
  const blank = () => lines.push('')
  const meta = data?.meta || {}
  const totals = data?.totals || {}

  row(['Отчёт: статистика репетитора'])
  row(['Сформирован', nowIso])
  row(['Период', `${meta.date_from || ''} — ${meta.date_to || ''}`])
  blank()

  if (options.summary) {
    row(['СВОДКА'])
    row(['Показатель', 'Значение'])
    const avg = totals.lessons ? Math.round(totals.revenue / totals.lessons) : 0
    const favg = totals.forecast_lessons ? Math.round(totals.forecast_revenue / totals.forecast_lessons) : 0
    const pairs = [
      ['Уроков', totals.lessons || 0],
      ['Часы репетитора', totals.tutor_hours || 0],
      ['Оплачиваемые часы', totals.billed_hours || 0],
      ['Выручка', totals.revenue || 0],
      ['Средний чек', avg],
      ['Прогноз уроков', totals.forecast_lessons || 0],
      ['Прогноз выручка', totals.forecast_revenue || 0],
      ['Прогноз средний чек', favg],
      ['Отмены', totals.cancelled_lessons || 0],
      ['Неявки', totals.no_show_lessons || 0],
      ['Упущено отменами и неявками', totals.lost_revenue || 0],
      ['Оценочных строк', totals.estimated_lines || 0],
      ['Занятость открытых часов, %', data?.capacity?.occupancy_pct ?? ''],
    ]
    for (const pair of pairs) row(pair)
    blank()
  }

  if (options.series) {
    row(['ДИНАМИКА'])
    row(['Период', 'Уроки', 'Выручка', 'Часы', 'Прогноз уроков', 'Прогноз выручка'])
    for (const s of data?.series || []) {
      row([s.bucket, s.lessons, s.revenue, s.tutor_hours, s.forecast_lessons, s.forecast_revenue])
    }
    blank()
  }

  if (options.students) {
    row(['УЧЕНИКИ'])
    row(['Ученик', 'Уроки', 'Часы', 'Выручка', 'Средний чек', 'Отмены', 'Неявки', 'Упущено',
      'Прогноз уроков', 'Прогноз выручка', 'Первая встреча', 'Последняя встреча'])
    for (const r of data?.by_student || []) {
      row([
        r.student_name, r.lessons, r.billed_hours, r.revenue,
        r.lessons ? Math.round(r.revenue / r.lessons) : 0,
        r.cancelled, r.no_show, r.lost_revenue || 0,
        r.forecast_lessons, r.forecast_revenue,
        r.first_lesson || '', r.last_lesson || '',
      ])
    }
    blank()
  }

  if (options.weekday) {
    row(['ДНИ НЕДЕЛИ'])
    row(['День', 'Уроки', 'Выручка'])
    for (const c of data?.by_weekday || []) {
      row([WEEKDAYS_FULL[c.weekday] || c.weekday, c.lessons, c.revenue])
    }
    blank()
  }

  if (options.hours) {
    row(['ЧАСЫ'])
    row(['День', 'Час', 'Уроки', 'Выручка'])
    for (const c of data?.by_hour || []) {
      row([WEEKDAYS_FULL[c.weekday] || c.weekday, c.hour, c.lessons, c.revenue])
    }
    blank()
  }

  if (options.upcoming) {
    row(['ПРОГНОЗ ЗАНЯТИЙ'])
    row(['Дата', 'Время', 'Ученик', 'Минут', 'Сумма'])
    for (const lesson of data?.upcoming || []) {
      for (const s of lesson.students || []) {
        row([lesson.date, `${lesson.start}-${lesson.end}`, s.student_name, lesson.minutes, s.amount])
      }
    }
    blank()
  }

  return '\uFEFF' + lines.join('\r\n')
}

// Статус ученика одной структурой: key для логики, label для показа.
export function studentStatus(firstLessonIso, lastLessonIso, todayIso, rangeFromIso = null) {
  const isNew = Boolean(rangeFromIso && firstLessonIso) && firstLessonIso >= rangeFromIso
  if (isNew) return { key: 'new', label: 'Новый', days: 0 }
  if (isInactiveStudent(lastLessonIso, todayIso, false)) {
    return { key: 'inactive', label: 'Пауза', days: daysSince(lastLessonIso, todayIso) }
  }
  return { key: 'active', label: 'Активен', days: 0 }
}

// Статус оплаты урока — по ручному флагу репетитора на каждой записи.
// Флаг хранится в записи участия, по умолчанию отсутствует = "нет".
// Отметить можно и непроведённый урок (предоплата) — логика та же.
// На цифры статистики не влияет, только метки.
export function lessonPayment(lesson) {
  if (!lesson) return { key: 'none', amount: 0 }
  const students = lesson.students || []
  const paidCount = students.filter((s) => s.paid).length
  const amount = lesson.total || 0
  const allPaid = students.length > 0 && paidCount === students.length
  const somePaid = paidCount > 0 && paidCount < students.length
  if (lesson.status === 'FINISHED') {
    if (allPaid) return { key: 'paid', amount }
    if (somePaid) {
      return { key: 'partial', amount, paidCount, totalCount: students.length }
    }
    return students.length ? { key: 'unpaid', amount } : { key: 'none', amount: 0 }
  }
  if (lesson.status === 'SCHEDULED' || lesson.status === 'ONGOING') {
    if (allPaid) return { key: 'paid', amount }
    if (somePaid) {
      return { key: 'partial', amount, paidCount, totalCount: students.length }
    }
    return { key: 'pending', amount: 0 }
  }
  return { key: 'none', amount: 0 }
}

export function paymentCellText(lesson) {
  const pay = lessonPayment(lesson)
  if (pay.key === 'paid') return 'да'
  if (pay.key === 'partial') return `частично (${pay.paidCount}/${pay.totalCount})`
  return ''
}

// Хронология уроков -> CSV. Оплата — вычисляемым значением (см. lessonPayment).
export function buildLessonsCsv(lessons) {
  const head = ['Дата', 'Время', 'Минуты', 'Тип', 'Ученики', 'Сумма', 'Оплата', 'Статус']
  const body = (lessons || []).map((l) => [
    l.date, l.start + '-' + l.end, l.minutes,
    l.is_group ? 'групповой' : 'индивидуальный',
    (l.students || []).map((s) => s.student_name).join(', '),
    l.total, paymentCellText(l), l.status,
  ])
  return '\uFEFF' + [head.map(csvEsc).join(';'), ...body.map((r) => r.map(csvEsc).join(';'))].join('\r\n')
}


// Хронология уроков -> данные для печати: заголовок, шапка, строки, итог.
export function buildLessonsPrintData(lessons, title, period) {
  const rows = (lessons || []).map((l) => [
    l.date ? l.date.split('-').reverse().join('.') : '—',
    `${l.start}-${l.end}`,
    (l.students || []).map((s) => s.student_name).join(', ') || '—',
    l.is_group ? 'группа' : 'инд.',
    String(l.total),
    paymentCellText(l) || '—',
  ])
  const minutes = (lessons || []).reduce((s, l) => s + (l.minutes || 0), 0)
  const total = (lessons || []).reduce((s, l) => s + (l.total || 0), 0)
  return {
    title,
    subtitle: period,
    head: ['Дата', 'Время', 'Ученики', 'Тип', 'Сумма', 'Оплата'],
    rows,
    foot: `Всего: ${lessons.length} ур. · ${Math.round(minutes / 60 * 100) / 100} ч · ${total} ₽`,
  }
}
