import { describe, it, expect } from 'vitest'
import {
  monthMatrix, monthRangeISO, shiftMonth, countByDay, dayLessons, lessonDate,
} from './calendar.js'

describe('monthMatrix', () => {
  it('недели с понедельника, ячейки заполнены полностью', () => {
    const weeks = monthMatrix(2030, 3) // март 2030: 1-е — пятница
    expect(weeks.every((w) => w.length === 7)).toBe(true)
    expect(weeks[0][0].day).toBe(25) // 25 февраля
    expect(weeks[0][0].inMonth).toBe(false)
    expect(weeks[0][4].day).toBe(1)
    expect(weeks[0][4].inMonth).toBe(true)
    // Март 2030 кончается в воскресенье — последняя ячейка в месяце.
    expect(weeks.at(-1).at(-1).iso).toBe('2030-03-31')
    expect(weeks.at(-1).at(-1).inMonth).toBe(true)
  })

  it('соседние месяца видны как дополнение', () => {
    const weeks = monthMatrix(2030, 1) // январь 2030: 1-е — вторник
    // Последняя неделя уходит в февраль.
    expect(weeks.at(-1).at(-1).iso).toBe('2030-02-03')
    expect(weeks.at(-1).at(-1).inMonth).toBe(false)
    expect(weeks[0][0].iso).toBe('2029-12-31')
    expect(weeks[0][0].inMonth).toBe(false)
  })

  it('февраль високосного года — 29 дней', () => {
    const weeks = monthMatrix(2028, 2)
    const days = weeks.flat().filter((c) => c.inMonth)
    expect(days).toHaveLength(29)
    expect(days.at(-1).iso).toBe('2028-02-29')
  })

  it('февраль обычного года — 28 дней', () => {
    const days = monthMatrix(2030, 2).flat().filter((c) => c.inMonth)
    expect(days).toHaveLength(28)
  })

  it('31-дневный месяц целиком в своём месяце', () => {
    const weeks = monthMatrix(2030, 1)
    const days = weeks.flat().filter((c) => c.inMonth)
    expect(days).toHaveLength(31)
    // Январь 2030 начинается со вторника — лишних рядов нет.
    expect(weeks).toHaveLength(5)
  })

  it('ISO-даты ячеек корректны', () => {
    const weeks = monthMatrix(2030, 12)
    const flat = weeks.flat()
    expect(flat[0].iso).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(flat.filter((c) => c.inMonth).at(-1).iso).toBe('2030-12-31')
  })
})

describe('monthRangeISO', () => {
  it('границы месяца полуоткрытые', () => {
    expect(monthRangeISO(2030, 2)).toEqual(['2030-02-01', '2030-03-01'])
    expect(monthRangeISO(2030, 12)).toEqual(['2030-12-01', '2031-01-01'])
  })
})

describe('shiftMonth', () => {
  it('переход через декабрь и январь', () => {
    expect(shiftMonth(2030, 12, 1)).toEqual({ year: 2031, month: 1 })
    expect(shiftMonth(2030, 1, -1)).toEqual({ year: 2029, month: 12 })
    expect(shiftMonth(2030, 5, 1)).toEqual({ year: 2030, month: 6 })
    expect(shiftMonth(2030, 5, -1)).toEqual({ year: 2030, month: 4 })
  })
})

function lesson(id, start) {
  return { lesson_id: id, start_time: start, end_time: start, status: 'SCHEDULED', is_group: false }
}

const LESSONS = [
  lesson(1, '2030-03-02 10:00:00'),
  lesson(2, '2030-03-02 08:00:00'),
  lesson(3, '2030-03-15 12:00:00'),
]

describe('lessonDate / countByDay / dayLessons', () => {
  it('дата урока — первые 10 символов start_time', () => {
    expect(lessonDate(LESSONS[0])).toBe('2030-03-02')
    expect(lessonDate(null)).toBe('')
  })

  it('countByDay считает уроки по дням', () => {
    expect(countByDay(LESSONS)).toEqual({ '2030-03-02': 2, '2030-03-15': 1 })
    expect(countByDay([])).toEqual({})
  })

  it('dayLessons отбирает день и сортирует по времени', () => {
    const day = dayLessons(LESSONS, '2030-03-02')
    expect(day.map((l) => l.lesson_id)).toEqual([2, 1])
    expect(dayLessons(LESSONS, '2030-04-01')).toEqual([])
  })
})
