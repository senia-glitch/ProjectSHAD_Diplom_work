import { describe, it, expect } from 'vitest'
import { formatMoney, formatHours, bucketLabel, isFutureBucket, daysSince, isNewStudent, isInactiveStudent, shiftRange, buildInsights, isoWeekRange, studentsToCsv, buildReport, defaultReportOptions, REPORT_SECTIONS, studentStatus, buildLessonsCsv, buildLessonsPrintData, lessonPayment, mondayOfIso, addDaysIso, monthRangeOf, resolveRequestRange } from './statistics.js'

describe('formatMoney', () => {
  it('форматирует рубли с группировкой', () => {
    expect(formatMoney(3000)).toContain('₽')
    expect(formatMoney(3000).replace(/\s/g, '')).toContain('3000')
    expect(formatMoney(0)).toContain('₽')
  })
})

describe('formatHours', () => {
  it('форматирует часы', () => {
    expect(formatHours(1.5)).toContain('ч')
    expect(formatHours(0)).toContain('ч')
  })
})

describe('bucketLabel', () => {
  it('подписывает корзины по шагу', () => {
    expect(bucketLabel('2030-03-02', 'day')).toBe('02.03')
    expect(bucketLabel('2030-03', 'month')).toBe('мар')
    expect(bucketLabel('2030-W10', 'week')).toBe('нед.10')
  })
})

describe('isFutureBucket', () => {
  it('будущее — строго после сегодня', () => {
    expect(isFutureBucket('2030-03-02', '2030-03-01')).toBe(true)
    expect(isFutureBucket('2030-03-01', '2030-03-01')).toBe(false)
    expect(isFutureBucket('2030-02-28', '2030-03-01')).toBe(false)
  })
})

describe('shiftRange', () => {
  it('сдвигает диапазон назад на его длину', () => {
    expect(shiftRange('2030-03-01', '2030-03-31')).toEqual(['2030-01-29', '2030-02-28'])
    expect(shiftRange('2030-01-01', '2030-12-31')).toEqual(['2029-01-01', '2029-12-31'])
  })
})

describe('buildReport', () => {
  const data = {
    meta: { date_from: '2030-01-01', date_to: '2030-12-31' },
    totals: {
      lessons: 1, tutor_hours: 1, billed_hours: 2, revenue: 3000,
      forecast_lessons: 1, forecast_revenue: 1800,
      cancelled_lessons: 0, no_show_lessons: 1, lost_revenue: 1800,
      estimated_lines: 0,
    },
    capacity: { occupancy_pct: 12 },
    series: [{ bucket: '2030-03', lessons: 1, revenue: 3000, tutor_hours: 1, forecast_lessons: 0, forecast_revenue: 0 }],
    by_student: [{
      student_name: 'Иван "А"', lessons: 1, billed_hours: 1, revenue: 1800,
      cancelled: 0, no_show: 0, lost_revenue: 0, forecast_lessons: 0,
      forecast_revenue: 0, first_lesson: '2030-03-02', last_lesson: '2030-03-02',
    }],
    by_weekday: [{ weekday: 5, lessons: 1, revenue: 3000 }],
    by_hour: [{ weekday: 5, hour: 10, lessons: 1, revenue: 3000 }],
    upcoming: [{
      date: '2030-06-02', start: '10:00', end: '11:00', minutes: 60,
      students: [{ student_name: 'Иван', amount: 1800 }],
    }],
  }
  it('полный отчёт: BOM, секции, экранирование', () => {
    const csv = buildReport(data, defaultReportOptions(), '2030-06-01T00:00:00')
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
    for (const name of ['СВОДКА', 'ДИНАМИКА', 'УЧЕНИКИ', 'ДНИ НЕДЕЛИ', 'ЧАСЫ', 'ПРОГНОЗ ЗАНЯТИЙ']) {
      expect(csv).toContain(name)
    }
    expect(csv).toContain('"Иван ""А"""')
    expect(csv).toContain('Суббота')
    expect(csv).toContain('2030-06-01T00:00:00')
  })
  it('выключенные разделы отсутствуют', () => {
    const csv = buildReport(data, { ...defaultReportOptions(), hours: false, upcoming: false })
    expect(csv).not.toContain('ЧАСЫ')
    expect(csv).not.toContain('ПРОГНОЗ ЗАНЯТИЙ')
    expect(csv).toContain('СВОДКА')
  })
  it('разделов шесть', () => {
    expect(REPORT_SECTIONS).toHaveLength(6)
  })
})

describe('isoWeekRange', () => {
  it('понедельник → воскресенье ISO-недели', () => {
    expect(isoWeekRange('2030-W10')).toEqual(['2030-03-04', '2030-03-10'])
    expect(isoWeekRange('2030-W01')).toEqual(['2029-12-31', '2030-01-06'])
  })
})

describe('studentsToCsv', () => {
  const rows = [{
    student_name: 'Иван "А"', lessons: 2, billed_hours: 3,
    revenue: 5400, forecast_revenue: 1800, forecast_lessons: 1,
    cancelled: 1, no_show: 0, estimated: 0,
  }]
  it('факт: шапка и экранирование', () => {
    const csv = studentsToCsv(rows, 'fact')
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
    expect(csv).toContain('Выручка')
    expect(csv).toContain('"Иван ""А"""')
    expect(csv).toContain('5400')
  })
  it('прогноз: свои колонки', () => {
    const csv = studentsToCsv(rows, 'forecast')
    expect(csv).toContain('Прогноз')
    expect(csv).not.toContain('Отмены')
  })
})

describe('buildInsights', () => {
  const data = {
    totals: { revenue: 3000 },
    series: [
      { bucket: '2030-03', bucket_start: '2030-03-01', lessons: 1, revenue: 3000 },
      { bucket: '2030-04', bucket_start: '2030-04-01', lessons: 0, revenue: 0 },
    ],
    by_student: [
      { student_id: 5, student_name: 'Иван', first_lesson: '2030-03-02', last_lesson: '2030-03-02' },
    ],
    capacity: { occupancy_pct: 12 },
    meta: { date_from: '2030-01-01', granularity: 'month' },
  }
  it('собирает дельту, лучшее, новичков и занятость', () => {
    const items = buildInsights(data, { revenue: 2000 }, '2030-06-01')
    const texts = items.map((i) => i.text)
    expect(texts.some((t) => t.includes('+50%'))).toBe(true)
    expect(texts.some((t) => t.includes('мар'))).toBe(true)
    expect(texts.some((t) => t.includes('Иван'))).toBe(true)
    expect(texts.some((t) => t.includes('12%'))).toBe(true)
    expect(items.length).toBeLessThanOrEqual(4)
  })
  it('пусто без данных', () => {
    expect(buildInsights(null, null, '2030-06-01')).toEqual([])
  })
})

describe('daysSince / isNewStudent / isInactiveStudent', () => {
  it('считает паузу в днях', () => {
    expect(daysSince('2030-03-02', '2030-04-11')).toBe(40)
    expect(daysSince('2030-03-02', '2030-03-02')).toBe(0)
  })
  it('новый — первая встреча внутри периода', () => {
    expect(isNewStudent('2030-03-02', '2030-03-01')).toBe(true)
    expect(isNewStudent('2030-02-28', '2030-03-01')).toBe(false)
    expect(isNewStudent(null, '2030-03-01')).toBe(false)
  })
  it('неактивен — не новый и пауза дольше порога', () => {
    expect(isInactiveStudent('2030-03-02', '2030-04-11', false)).toBe(true)
    expect(isInactiveStudent('2030-04-01', '2030-04-11', false)).toBe(false)
    expect(isInactiveStudent('2030-03-02', '2030-04-11', true)).toBe(false)
  })
})


describe('studentStatus', () => {
  it('новый / неактивен / активен', () => {
    expect(studentStatus('2030-03-02', '2030-03-02', '2030-06-01', '2030-03-01')).toEqual({ key: 'new', label: 'Новый', days: 0 })
    const st = studentStatus('2029-01-05', '2030-03-02', '2030-06-01', '2030-05-01')
    expect(st.key).toBe('inactive')
    expect(st.days).toBe(91)
    expect(studentStatus('2029-01-05', '2030-05-20', '2030-06-01', '2030-05-01')).toEqual({ key: 'active', label: 'Активен', days: 0 })
  })
})

describe('buildLessonsCsv', () => {
  const lessons = [{
    date: '2030-03-02', start: '10:00', end: '11:00', minutes: 60,
    is_group: false, status: 'FINISHED', total: 1800,
    students: [{ student_name: 'Иван' }],
  }]
  it('колонки по ТЗ с BOM, без оплаты', () => {
    const csv = buildLessonsCsv(lessons)
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
    expect(csv).toContain('"Дата";"Время";"Минуты";"Тип";"Ученики";"Сумма";"Оплата";"Статус"')
    expect(csv).toContain('2030-03-02')
    expect(csv).toContain('1800')
  })
})

describe('lessonPayment', () => {
  const paid = { student_id: 5, paid: true }
  const unpaid = { student_id: 6, paid: false }
  it('все записи оплачены — paid', () => {
    expect(lessonPayment({ status: 'FINISHED', total: 3000, students: [paid, { ...paid, student_id: 6 }] }))
      .toEqual({ key: 'paid', amount: 3000 })
  })
  it('никто не оплачен — unpaid', () => {
    expect(lessonPayment({ status: 'FINISHED', total: 3000, students: [unpaid] }))
      .toEqual({ key: 'unpaid', amount: 3000 })
  })
  it('частично — partial со счётчиками', () => {
    expect(lessonPayment({ status: 'FINISHED', total: 3000, students: [paid, unpaid] }))
      .toEqual({ key: 'partial', amount: 3000, paidCount: 1, totalCount: 2 })
  })
  it('запланированный — ожидает, но предоплата видна', () => {
    expect(lessonPayment({ status: 'SCHEDULED', total: 1800, students: [{ paid: false }] }))
      .toEqual({ key: 'pending', amount: 0 })
    expect(lessonPayment({ status: 'SCHEDULED', total: 1800, students: [{ paid: true }] }))
      .toEqual({ key: 'paid', amount: 1800 })
    expect(lessonPayment({
      status: 'ONGOING', total: 3600, students: [{ paid: true }, { paid: false }],
    })).toEqual({ key: 'partial', amount: 3600, paidCount: 1, totalCount: 2 })
  })
  it('отмена и неявка — нет оплаты', () => {
    expect(lessonPayment({ status: 'CANCELLED', total: 1800, students: [paid] }))
      .toEqual({ key: 'none', amount: 0 })
    expect(lessonPayment({ status: 'FINISHED', total: 0, students: [] }))
      .toEqual({ key: 'none', amount: 0 })
  })
})

describe('buildLessonsPrintData', () => {
  it('шапка, строки, итог', () => {
    const doc = buildLessonsPrintData([{
      date: '2030-03-02', start: '10:00', end: '11:00', minutes: 60,
      is_group: true, status: 'FINISHED', total: 3000,
      students: [{ student_name: 'Иван' }, { student_name: 'Пётр' }],
    }], 'Уроки', 'март')
    expect(doc.head).toHaveLength(6)
    expect(doc.rows).toHaveLength(1)
    expect(doc.rows[0][2]).toContain('Иван')
    expect(doc.foot).toContain('3000')
  })
})

describe('mondayOfIso / addDaysIso / monthRangeOf', () => {
  it('понедельник недели', () => {
    expect(mondayOfIso('2026-10-09')).toBe('2026-10-05')
    expect(mondayOfIso('2026-10-05')).toBe('2026-10-05')
    expect(mondayOfIso('2026-10-11')).toBe('2026-10-05')
    expect(mondayOfIso('мусор')).toBeNull()
    expect(mondayOfIso('')).toBeNull()
  })
  it('сдвиг дней', () => {
    expect(addDaysIso('2026-10-05', 6)).toBe('2026-10-11')
    expect(addDaysIso('2026-12-30', 5)).toBe('2027-01-04')
    expect(addDaysIso('нет', 1)).toBeNull()
  })
  it('границы месяца', () => {
    expect(monthRangeOf('2026-02')).toEqual(['2026-02-01', '2026-02-28'])
    expect(monthRangeOf('2024-02')).toEqual(['2024-02-01', '2024-02-29'])
    expect(monthRangeOf('2026-13')).toBeNull()
    expect(monthRangeOf('')).toBeNull()
  })
})

describe('resolveRequestRange', () => {
  it('пресеты дают валидный диапазон', () => {
    expect(resolveRequestRange({ preset: 'year', year: 2026 }))
      .toEqual({ year: 2026, dateFrom: '2026-01-01', dateTo: '2026-12-31' })
    expect(resolveRequestRange({ preset: 'month', year: 2026, month: '2026-03' }))
      .toEqual({ year: 2026, dateFrom: '2026-03-01', dateTo: '2026-03-31' })
    expect(resolveRequestRange({ preset: 'week', year: 2026, weekAnchor: '2026-10-09' }))
      .toEqual({ year: 2026, dateFrom: '2026-10-05', dateTo: '2026-10-11' })
    expect(resolveRequestRange({ preset: 'custom', year: 2026, customFrom: '2026-05-10', customTo: '2026-05-01' }))
      .toEqual({ year: 2026, dateFrom: '2026-05-01', dateTo: '2026-05-10' })
  })
  it('год выводится из дат, а не наоборот', () => {
    // Кейс пропадавшего графика: якорь недели из другого года, чем выбранный год.
    expect(resolveRequestRange({ preset: 'week', year: 2025, weekAnchor: '2026-10-09' }))
      .toEqual({ year: 2026, dateFrom: '2026-10-05', dateTo: '2026-10-11' })
    expect(resolveRequestRange({ preset: 'month', year: 2025, month: '2026-03' }))
      .toEqual({ year: 2026, dateFrom: '2026-03-01', dateTo: '2026-03-31' })
  })
  it('мусор откатывается на год', () => {
    expect(resolveRequestRange({ preset: 'week', year: 2026, weekAnchor: 'мусор' }))
      .toEqual({ year: 2026, dateFrom: '2026-01-01', dateTo: '2026-12-31' })
    expect(resolveRequestRange({ preset: 'custom', year: 2026, customFrom: '', customTo: '' }))
      .toEqual({ year: 2026, dateFrom: '2026-01-01', dateTo: '2026-12-31' })
    expect(resolveRequestRange({ preset: 'year', year: 1999 }))
      .toEqual({ year: new Date().getFullYear(), dateFrom: `${new Date().getFullYear()}-01-01`, dateTo: `${new Date().getFullYear()}-12-31` })
  })
})
