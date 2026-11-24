import { describe, it, expect } from 'vitest'
import { groupUpcoming, upcomingRange } from './upcoming.js'

const L = (id, start, end, status = 'SCHEDULED') => ({ lesson_id: id, start_time: start, end_time: end, status })

describe('ближайшие уроки', () => {
  const now = '2026-11-25T12:00:00'

  it('диапазон загрузки: месяц назад и неделя вперёд', () => {
    expect(upcomingRange(now)).toEqual({ dateFrom: '2026-10-26', dateTo: '2026-12-02' })
  })

  it('активные на неделю по дням, прошедшие и дальние отброшены', () => {
    const { days, pendingCount } = groupUpcoming([
      L(1, '2026-11-25T10:00:00', '2026-11-25T11:00:00'), // уже прошёл
      L(2, '2026-11-25T11:30:00', '2026-11-25T12:30:00', 'ONGOING'), // идёт сейчас
      L(3, '2026-11-26T09:00:00', '2026-11-26T10:00:00', 'PENDING'),
      L(4, '2026-11-26T08:00:00', '2026-11-26T09:00:00'),
      L(5, '2026-12-10T08:00:00', '2026-12-10T09:00:00'), // дальше недели
      L(6, '2026-11-27T08:00:00', '2026-11-27T09:00:00', 'CANCELLED'),
    ], now)
    expect(days.map((d) => d.label)).toEqual(['Сегодня', 'Завтра'])
    expect(days[1].lessons.map((l) => l.lesson_id)).toEqual([4, 3])
    expect(pendingCount).toBe(1)
  })

  it('история отмен — новые сверху, только за 30 дней', () => {
    const { history } = groupUpcoming([
      L(1, '2026-11-20T10:00:00', '2026-11-20T11:00:00', 'CANCELLED'),
      L(2, '2026-11-27T10:00:00', '2026-11-27T11:00:00', 'REJECTED'),
      L(3, '2026-09-01T10:00:00', '2026-09-01T11:00:00', 'CANCELLED'),
      L(4, '2026-11-24T10:00:00', '2026-11-24T11:00:00', 'SYSTEM_FINISHED'),
    ], now)
    expect(history.map((l) => l.lesson_id)).toEqual([2, 4, 1])
  })
})
