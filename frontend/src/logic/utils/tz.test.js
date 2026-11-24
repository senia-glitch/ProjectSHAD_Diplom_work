import { describe, it, expect, afterEach } from 'vitest'
import {
  shiftIso,
  toUserTime,
  toServerTime,
  rangeToServer,
  lessonToUser,
  registerOffsetProvider,
  currentOffset,
} from './tz.js'

afterEach(() => registerOffsetProvider(() => 0))

describe('личный пояс на границе API', () => {
  it('сдвигает наивное время через полночь и месяц', () => {
    expect(shiftIso('2026-11-30T20:00:00', 8)).toBe('2026-12-01T04:00:00')
    expect(shiftIso('2026-12-01T03:00', -8)).toBe('2026-11-30T19:00:00')
    expect(shiftIso('2026-11-30 20:00:00', 0)).toBe('2026-11-30T20:00:00')
    expect(shiftIso('не время', 3)).toBe('не время')
  })

  it('туда и обратно — то же время', () => {
    expect(toServerTime(toUserTime('2026-11-26T02:00:00', 8), 8)).toBe('2026-11-26T02:00:00')
  })

  it('местная неделя превращается в полуоткрытый UTC-период', () => {
    expect(rangeToServer('2026-11-23', '2026-11-29', 8)).toEqual({
      dateFrom: '2026-11-22T16:00:00',
      dateTo: '2026-11-29T16:00:00',
    })
  })

  it('урок с пометками и историей переводится целиком', () => {
    const lesson = lessonToUser({
      start_time: '2026-11-26T02:00:00',
      end_time: '2026-11-26T03:00:00',
      status_note: { status: 'CANCELLED', by: 'student', at: '2026-11-25T20:00:00' },
      status_history: [{ status: 'SCHEDULED', at: '2026-11-25T10:00:00' }],
      absence: { status: 'VACATION', from: '2026-11-25T16:00:00', to: '2026-12-01T16:00:00' },
      cancel_deadline: '2026-11-25T02:00:00',
    }, 8)
    expect(lesson.start_time).toBe('2026-11-26T10:00:00')
    expect(lesson.status_note.at).toBe('2026-11-26T04:00:00')
    expect(lesson.status_history[0].at).toBe('2026-11-25T18:00:00')
    expect(lesson.absence.from).toBe('2026-11-26T00:00:00')
    expect(lesson.cancel_deadline).toBe('2026-11-25T10:00:00')
  })

  it('пояс берётся у провайдера сессии', () => {
    registerOffsetProvider(() => -5)
    expect(currentOffset()).toBe(-5)
    expect(toUserTime('2026-11-26T02:00:00')).toBe('2026-11-25T21:00:00')
  })
})
