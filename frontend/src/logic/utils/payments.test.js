import { describe, it, expect } from 'vitest'
import { buildPaymentRows, summarizePayments, filterPaymentRows } from './payments.js'

function lesson(id, date, start, students) {
  return {
    lesson_id: id, date, start, end: '11:00', minutes: 60,
    is_group: false, status: 'FINISHED', descriptions: null, links: [], students, total: 0,
  }
}

function student(id, name, amount, paid) {
  return { student_id: id, student_user_id: id + 100, student_name: name, amount, estimated: false, paid }
}

const LESSONS = [
  lesson(1, '2030-03-02', '10:00', [student(5, 'Иван', 1800, true)]),
  lesson(2, '2030-03-03', '10:00', [
    student(5, 'Иван', 1800, false),
    student(6, 'Мария', 2000, true),
  ]),
]

describe('buildPaymentRows', () => {
  it('разворачивает уроки в строки «ученик × урок»', () => {
    const rows = buildPaymentRows(LESSONS)
    expect(rows).toHaveLength(3)
    const row = rows[0]
    expect(row).toMatchObject({
      lesson_id: 2, date: '2030-03-03', start: '10:00',
      student_id: 5, student_user_id: 105, student_name: 'Иван', amount: 1800, paid: false,
    })
  })

  it('сохраняет порядок учеников внутри одного урока', () => {
    const rows = buildPaymentRows(LESSONS)
    expect(rows.slice(0, 2).map((r) => r.student_id)).toEqual([5, 6])
  })

  it('сортирует новые сверху', () => {
    const rows = buildPaymentRows(LESSONS)
    expect(rows[0].date).toBe('2030-03-03')
    expect(rows[rows.length - 1].date).toBe('2030-03-02')
  })

  it('пустые и битые данные не ломают разбор', () => {
    expect(buildPaymentRows([])).toEqual([])
    expect(buildPaymentRows(null)).toEqual([])
    expect(buildPaymentRows([{ lesson_id: 1, date: '2030-03-02', start: '10:00' }])).toEqual([])
  })
})

describe('summarizePayments', () => {
  it('считает собрано и долг общий и по ученикам', () => {
    const { collected, debt, byStudent } = summarizePayments(buildPaymentRows(LESSONS))
    expect(collected).toBe(3800)
    expect(debt).toBe(1800)
    expect(byStudent).toEqual([
      { student_id: 5, student_name: 'Иван', collected: 1800, debt: 1800 },
      { student_id: 6, student_name: 'Мария', collected: 2000, debt: 0 },
    ])
  })

  it('должники идут первыми', () => {
    const { byStudent } = summarizePayments(buildPaymentRows(LESSONS))
    expect(byStudent[0].debt).toBeGreaterThanOrEqual(byStudent[1].debt)
  })

  it('пустой реестр — нули', () => {
    expect(summarizePayments([])).toEqual({ collected: 0, debt: 0, byStudent: [] })
  })
})

describe('filterPaymentRows', () => {
  const rows = buildPaymentRows(LESSONS)

  it('all — без фильтра', () => {
    expect(filterPaymentRows(rows, 'all')).toHaveLength(3)
  })

  it('paid — только оплаченные', () => {
    expect(filterPaymentRows(rows, 'paid')).toHaveLength(2)
    expect(filterPaymentRows(rows, 'paid').every((r) => r.paid)).toBe(true)
  })

  it('unpaid — только неоплаченные', () => {
    expect(filterPaymentRows(rows, 'unpaid')).toHaveLength(1)
    expect(filterPaymentRows(rows, 'unpaid')[0].student_id).toBe(5)
  })
})
