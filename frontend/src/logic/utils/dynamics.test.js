import { describe, it, expect } from 'vitest'
import {
  pivotYear, cellValue, matrixMax, shadeLevel, fmtCellValue, fmtCompactRu,
  isoWeeksOfYear, weekSpan, linesInRange, filterLines, aggregateReport,
  daysBetweenInclusive, reportToCsv, daysInMonth, alignSeries,
} from './dynamics.js'

let __lid = 1
const L = (date, status, extra = {}) => ({
  lesson_id: extra.lesson_id ?? __lid++,
  date, start: '10:00', end: '11:00', minutes: extra.minutes ?? 60,
  is_group: false, status, total: extra.total ?? 1000,
  links: [], students: extra.students ?? [],
})

const S = (name, amount, paid) => ({ student_id: 1, name, amount, paid })

describe('pivotYear', () => {
  it('кладет уроки по дням, несуществующие дни помечает', () => {
    const grid = pivotYear([L('2026-02-28', 'FINISHED')], 2026)
    expect(grid).toHaveLength(12)
    expect(grid[1][27].exists).toBe(true)
    expect(grid[1][27].lessons).toHaveLength(1)
    expect(grid[1][28].exists).toBe(false)
    expect(grid[1][28].lessons).toHaveLength(0)
    expect(grid[0]).toHaveLength(31)
  })
  it('29 февраля високосного существует', () => {
    const grid = pivotYear([], 2024)
    expect(grid[1][28].exists).toBe(true)
  })
})

describe('cellValue', () => {
  const day = [
    L('2026-05-10', 'FINISHED', { students: [S('А', 1000, true), S('Б', 1000, false)], total: 2000 }),
    L('2026-05-10', 'SCHEDULED', { students: [S('В', 1500, false)], total: 1500 }),
    L('2026-05-10', 'CANCELLED', { students: [], total: 0 }),
  ]
  it('считает по статусам', () => {
    expect(cellValue(day, 'conducted')).toBe(1)
    expect(cellValue(day, 'planned')).toBe(1)
    expect(cellValue(day, 'cancelled')).toBe(1)
  })
  it('выручка — только оплаченные линии проведённых', () => {
    expect(cellValue(day, 'revenue')).toBe(1000)
    expect(cellValue(day, 'paid')).toBe(1000)
    expect(cellValue(day, 'unpaid')).toBe(1000)
  })
  it('время — часы проведённых', () => {
    expect(cellValue(day, 'time')).toBe(1)
  })
})

describe('matrixMax + shadeLevel', () => {
  it('ноль = пусто = не красим', () => {
    expect(shadeLevel(0, 10)).toBe(0)
    expect(shadeLevel(5, 0)).toBe(0)
    expect(shadeLevel(0, 0)).toBe(0)
  })
  it('5 оттенков шагом 20%', () => {
    expect(shadeLevel(1, 100)).toBe(1)
    expect(shadeLevel(20, 100)).toBe(1)
    expect(shadeLevel(21, 100)).toBe(2)
    expect(shadeLevel(100, 100)).toBe(5)
  })
  it('matrixMax ищет максимум видимых', () => {
    const grid = pivotYear([L('2026-01-05', 'FINISHED')], 2026)
    expect(matrixMax(grid, 'conducted')).toBe(1)
    expect(matrixMax(grid, 'revenue')).toBe(0)
  })
})

describe('fmtCellValue', () => {
  it('пусто для нуля', () => {
    expect(fmtCellValue(0, 'conducted')).toBe('')
    expect(fmtCellValue(0, 'revenue')).toBe('')
  })
  it('время с 1 знаком', () => {
    expect(fmtCellValue(7.5, 'time')).toBe('7,5')
    expect(fmtCellValue(8, 'time')).toBe('8')
  })
  it('выручка компактно', () => {
    expect(fmtCompactRu(950)).toBe('950')
    expect(fmtCompactRu(1240)).toBe('1,2к')
    expect(fmtCellValue(2000, 'revenue')).toBe('2к')
  })
})

describe('isoWeeksOfYear', () => {
  it('недели Пн–Вс покрывают год', () => {
    const weeks = isoWeeksOfYear(2026)
    expect(weeks.length).toBeGreaterThanOrEqual(52)
    expect(weeks.length).toBeLessThanOrEqual(53)
    for (const w of weeks) {
      expect(new Date(`${w.from}T12:00:00`).getDay()).toBe(1)
      expect(new Date(`${w.to}T12:00:00`).getDay()).toBe(0)
    }
    expect(weeks[0].from <= '2026-01-01').toBe(true)
    expect(weeks[weeks.length - 1].to >= '2026-12-31').toBe(true)
  })
  it('стыковая неделя лежит в двух месяцах одной карточкой', () => {
    const weeks = isoWeeksOfYear(2026)
    const spanning = weeks.filter((w) => w.fromM !== w.toM)
    expect(spanning.length).toBeGreaterThan(0)
    for (const w of spanning) {
      expect(Math.abs(w.toM - w.fromM)).toBeLessThanOrEqual(11)
    }
  })
})

describe('linesInRange + filterLines', () => {
  const lessons = [
    L('2026-03-01', 'FINISHED', { students: [S('А', 1000, true)] }),
    L('2026-03-05', 'SCHEDULED', { students: [S('Б', 500, false)] }),
    L('2026-04-01', 'FINISHED', { students: [S('А', 1000, true)] }),
  ]
  it('режет по диапазону и сортирует', () => {
    const rows = linesInRange(lessons, '2026-03-01', '2026-03-31')
    expect(rows).toHaveLength(2)
    expect(rows[0].date).toBe('2026-03-01')
  })
  it('гибкое включение: статус И оплата', () => {
    const rows = linesInRange(lessons, '2026-03-01', '2026-04-30')
    expect(filterLines(rows, {}).length).toBe(3)
    expect(filterLines(rows, { conducted: false }).length).toBe(1)
    expect(filterLines(rows, { paid: false }).every((r) => !r.paid)).toBe(true)
  })
})

describe('aggregateReport', () => {
  const lessons = [
    L('2026-03-01', 'FINISHED', { minutes: 60, total: 2000, students: [S('А', 1000, true), S('Б', 1000, false)] }),
    L('2026-03-02', 'SCHEDULED', { minutes: 90, total: 1500, students: [S('В', 1500, false)] }),
    L('2026-03-03', 'CANCELLED', { minutes: 60, total: 0, students: [] }),
  ]
  const rows = linesInRange(lessons, '2026-03-01', '2026-03-31')
  const agg = aggregateReport(lessons.filter((l) => l.date.startsWith('2026-03')), rows, 31)
  it('финансы', () => {
    expect(agg.finance.revenue).toBe(1000)
    expect(agg.finance.avgPaid).toBe(1000)
    expect(agg.finance.avgPlanned).toBe(1500)
  })
  it('кольцо уроков без отмен на диаграмме', () => {
    expect(agg.lessonsDonut.conducted).toBe(1)
    expect(agg.lessonsDonut.planned).toBe(1)
    expect(agg.lessonsDonut.cancelled).toBe(1)
    expect(agg.lessonsDonut.cancelledByStudent).toBe(0)
    expect(agg.lessonsDonut.cancelledByTutor).toBe(0)
  })
  it('кольцо времени: целое — календарь', () => {
    expect(agg.timeDonut.periodH).toBe(31 * 24)
    expect(agg.timeDonut.conductedH).toBe(1)
    expect(agg.timeDonut.plannedH).toBe(1.5)
    expect(agg.timeDonut.freeH).toBe(31 * 24 - 2.5)
  })
})

describe('daysBetweenInclusive + reportToCsv', () => {
  it('дни включительно', () => {
    expect(daysBetweenInclusive('2026-03-01', '2026-03-01')).toBe(1)
    expect(daysBetweenInclusive('2026-03-01', '2026-03-31')).toBe(31)
  })
  it('csv с BOM и секциями', () => {
    const csv = reportToCsv({ title: 'T', rangeLabel: 'R', agg: aggregateReport([], [], 1), rows: [], showLinks: false })
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
    expect(csv).toContain('ФИНАНСЫ')
    expect(csv).toContain('СПИСОК')
  })
})

describe('weekSpan', () => {
  it('стык лет обрезается по году', () => {
    // Неделя Пн 29.12.2025 – Вс 04.01.2026 в сетке 2026: только январь.
    const w = { fromM: 11, toM: 0, fromY: 2025, toY: 2026 }
    expect(weekSpan(2026, w)).toEqual({ start: 1, span: 1 })
    // Неделя Пн 28.12.2026 – Вс 03.01.2027 в сетке 2026: только декабрь.
    const w2 = { fromM: 11, toM: 0, fromY: 2026, toY: 2027 }
    expect(weekSpan(2026, w2)).toEqual({ start: 12, span: 1 })
    // Обычная: март–апрель.
    expect(weekSpan(2026, { fromM: 2, toM: 3, fromY: 2026, toY: 2026 })).toEqual({ start: 3, span: 2 })
  })
})

describe('aggregateReport время по урокам', () => {
  it('группа не умножает часы: сплиты сходятся с сегментом', () => {
    const lessons = [
      L('2026-03-01', 'FINISHED', { minutes: 60, students: [S('А', 1000, true), S('Б', 1000, true), S('В', 1000, false)] }),
    ]
    const rows = linesInRange(lessons, '2026-03-01', '2026-03-31')
    const agg = aggregateReport(lessons, rows, 31)
    expect(agg.timeDonut.conductedH).toBe(1)
    expect(agg.timeDonut.conductedPaidH).toBeCloseTo(0.7, 1)
    expect(agg.timeDonut.conductedUnpaidH).toBeCloseTo(0.3, 1)
  })
  it('урок без записей — время в неоплаченные', () => {
    const lessons = [L('2026-03-01', 'FINISHED', { minutes: 60, students: [] })]
    const rows = linesInRange(lessons, '2026-03-01', '2026-03-31')
    const agg = aggregateReport(lessons, rows, 31)
    expect(agg.timeDonut.conductedUnpaidH).toBe(1)
    expect(agg.timeDonut.conductedPaidH).toBe(0)
  })
})

describe('alignSeries', () => {
  it('разреженный ряд натягивается на полную сетку с нулями', () => {
    const buckets = ['2026-09', '2026-10', '2026-11']
    const cells = [{ bucket: '2026-09', revenue: 1000, forecast: 0 }]
    const out = alignSeries(buckets, cells)
    expect(out).toHaveLength(3)
    expect(out[0]).toEqual({ bucket: '2026-09', revenue: 1000, forecast: 0 })
    expect(out[1]).toEqual({ bucket: '2026-10', revenue: 0, forecast: 0 })
    expect(out[2].bucket).toBe('2026-11')
  })
})

describe('aggregateReport инициаторы', () => {
  it('cancelCounts попадают в легенду, без них — нули', () => {
    const lessons = [L('2026-03-01', 'CANCELLED', { students: [] })]
    const rows = linesInRange(lessons, '2026-03-01', '2026-03-31')
    const withCounts = aggregateReport(lessons, rows, 31, { byStudent: 2, byTutor: 3 })
    expect(withCounts.lessonsDonut.cancelledByStudent).toBe(2)
    expect(withCounts.lessonsDonut.cancelledByTutor).toBe(3)
    expect(withCounts.lessonsDonut.cancelled).toBe(1)
    const without = aggregateReport(lessons, rows, 31)
    expect(without.lessonsDonut.cancelledByStudent).toBe(0)
    expect(without.lessonsDonut.cancelledByTutor).toBe(0)
    expect(without.lessonsDonut.cancelledStub).toBeUndefined()
  })
})

describe('daysInMonth', () => {
  it('февраль', () => {
    expect(daysInMonth(2026, 1)).toBe(28)
    expect(daysInMonth(2024, 1)).toBe(29)
  })
})
