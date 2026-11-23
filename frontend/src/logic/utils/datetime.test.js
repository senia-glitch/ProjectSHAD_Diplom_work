import { describe, it, expect } from 'vitest'
import { toDateStr, toMinutes, toMin, fmtTime, fmtDateTime, fmtDate, toIso, dateOf, getWeekStart, nearestWeekday } from './datetime.js'

describe('toDateStr', () => {
  it('режет ISO с T и с пробелом', () => {
    expect(toDateStr('2026-09-24T02:01:00')).toBe('2026-09-24')
    expect(toDateStr('2026-09-24 02:01:00')).toBe('2026-09-24')
    expect(toDateStr('')).toBe('')
  })
})

describe('toMinutes', () => {
  it('считает минуты от полуночи', () => {
    expect(toMinutes('2026-09-24T02:01:00')).toBe(121)
    expect(toMinutes('2026-09-24 23:59:00')).toBe(23 * 60 + 59)
  })
})

describe('toMin', () => {
  it('парсит HH:MM[:SS]', () => {
    expect(toMin('09:00')).toBe(540)
    expect(toMin('09:00:00')).toBe(540)
  })
})

describe('fmtTime / fmtDateTime', () => {
  it('форматирует время и дату-время', () => {
    expect(fmtTime('2026-09-24T02:01:00')).toBe('02:01')
    expect(fmtTime('2026-09-24 02:01:00')).toBe('02:01')
    expect(fmtDateTime('2026-09-24T02:01:00')).toBe('2026-09-24 02:01')
    expect(fmtTime('')).toBe('')
  })
})

describe('getWeekStart', () => {
  it('возвращает понедельник недели', () => {
    expect(fmtDate(getWeekStart(new Date(2026, 8, 23)))).toBe('2026-09-21')
    expect(fmtDate(getWeekStart(new Date(2026, 8, 27)))).toBe('2026-09-21')
  })
})

describe('fmtDate / toIso / dateOf', () => {
  it('собирает YYYY-MM-DD и нормализует значения', () => {
    expect(fmtDate(new Date(2026, 8, 5))).toBe('2026-09-05')
    expect(toIso('2026-09-24 02:01')).toBe('2026-09-24T02:01')
    expect(dateOf('2026-09-24T02:01:00')).toBe('2026-09-24')
    expect(dateOf(new Date(2026, 8, 5))).toBe('2026-09-05')
  })
})

describe('nearestWeekday', () => {
  it('возвращает ближайшее вхождение дня, включая сегодня', () => {
    const wed = new Date('2026-09-23T12:00')
    expect(nearestWeekday(3, wed)).toBe('2026-09-23')
    expect(nearestWeekday(1, wed)).toBe('2026-09-28')
    expect(nearestWeekday(0, wed)).toBe('2026-09-27')
  })
})
