// Тесты сетки шага записи: примеры из спецификации.
import { describe, expect, test } from 'vitest'
import {
  buildStartGrid,
  buildDurations,
  findWindow,
  validateItemAgainstWindows,
  slotRangeFromSlot,
  buildStudentPreview,
  generateWeeklyDates,
  resolveTutorColor,
  lessonLinksVisible,
  lessonLinksRemainingMin,
  fmtDur,
  toHHMM,
} from './schedule-steps.js'

const M = (h, m = 0) => h * 60 + m

describe('buildStartGrid', () => {
  test('60 / 09:00–12:00 → 09:00, 10:00, 11:00', () => {
    expect(buildStartGrid(M(9), M(12), 60).map(toHHMM)).toEqual(['09:00', '10:00', '11:00'])
  })
  test('60 / 09:00–11:30 → 09:00, 10:00', () => {
    expect(buildStartGrid(M(9), M(11, 30), 60).map(toHHMM)).toEqual(['09:00', '10:00'])
  })
  test('60 / 09:00–09:45 (окно короче шага) → 09:00', () => {
    expect(buildStartGrid(M(9), M(9, 45), 60)).toEqual([M(9)])
  })
  test('30 / 09:00–11:00 → 09:00, 09:30, 10:00, 10:30', () => {
    expect(buildStartGrid(M(9), M(11), 30).map(toHHMM)).toEqual(['09:00', '09:30', '10:00', '10:30'])
  })
  test('30 / 09:00–11:10 → 09:00, 09:30, 10:00, 10:30', () => {
    expect(buildStartGrid(M(9), M(11, 10), 30).map(toHHMM)).toEqual(['09:00', '09:30', '10:00', '10:30'])
  })
  test('пустое и перевёрнутое окно', () => {
    expect(buildStartGrid(M(9), M(9), 60)).toEqual([])
    expect(buildStartGrid(M(10), M(9), 60)).toEqual([])
  })
})

describe('buildDurations', () => {
  test('60 / старт 09:00, окно до 12:00 → 60, 120, 180 без дубля', () => {
    expect(buildDurations(M(9), M(12), 60)).toEqual([
      { minutes: 60, kind: 'step' },
      { minutes: 120, kind: 'step' },
      { minutes: 180, kind: 'step' },
    ])
  })
  test('60 / старт 09:00, окно до 11:30 → 60, 120 + окно 150', () => {
    expect(buildDurations(M(9), M(11, 30), 60)).toEqual([
      { minutes: 60, kind: 'step' },
      { minutes: 120, kind: 'step' },
      { minutes: 150, kind: 'window' },
    ])
  })
  test('60 / окно 09:00–09:45, старт 09:00 → только окно 45', () => {
    expect(buildDurations(M(9), M(9, 45), 60)).toEqual([{ minutes: 45, kind: 'window' }])
  })
  test('60 / старт 10:00, окно до 11:30 → 60 + окно 90', () => {
    expect(buildDurations(M(10), M(11, 30), 60)).toEqual([
      { minutes: 60, kind: 'step' },
      { minutes: 90, kind: 'window' },
    ])
  })
  test('30 / старт 09:30, окно до 11:10 → кратные + окно 100', () => {
    const out = buildDurations(M(9, 30), M(11, 10), 30)
    expect(out.filter((d) => d.kind === 'step').map((d) => d.minutes)).toEqual([30, 60, 90])
    expect(out[out.length - 1]).toEqual({ minutes: 100, kind: 'window' })
  })
})

describe('findWindow + validate', () => {
  const ws = [
    { start: '2026-09-28T09:00:00', end: '2026-09-28T11:30:00' },
  ]
  test('внутри окна — ок', () => {
    expect(
      validateItemAgainstWindows({ start: '2026-09-28T10:00', end: '2026-09-28T11:00' }, ws, 60),
    ).toEqual({ ok: true, reason: '' })
  })
  test('вариант (б) — ок без кратности', () => {
    expect(
      validateItemAgainstWindows({ start: '2026-09-28T09:00', end: '2026-09-28T11:30' }, ws, 60),
    ).toEqual({ ok: true, reason: '' })
  })
  test('вне окна', () => {
    expect(
      validateItemAgainstWindows({ start: '2026-09-28T12:00', end: '2026-09-28T13:00' }, ws, 60),
    ).toEqual({ ok: false, reason: 'outside' })
  })
  test('старт вне сетки', () => {
    expect(
      validateItemAgainstWindows({ start: '2026-09-28T09:15', end: '2026-09-28T10:15' }, ws, 60),
    ).toEqual({ ok: false, reason: 'off-grid' })
  })
  test('длительность не кратна и не до конца окна', () => {
    expect(
      validateItemAgainstWindows({ start: '2026-09-28T09:00', end: '2026-09-28T10:30' }, ws, 60),
    ).toEqual({ ok: false, reason: 'bad-duration' })
  })
})

describe('slotRangeFromSlot', () => {
  test('dates: мин–макс', () => {
    const r = slotRangeFromSlot({
      mode: 'dates',
      dates: [{ date: '2026-10-05' }, { date: '' }, { date: '2026-09-28' }],
    })
    expect(r).toEqual({ dateFrom: '2026-09-28', dateTo: '2026-10-05' })
  })
  test('dates без дат — null', () => {
    expect(slotRangeFromSlot({ mode: 'dates', dates: [] })).toBeNull()
  })
  test('weekly: диапазон объединением по дням', () => {
    const weekdays = {}
    for (const d of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
      weekdays[d] = { on: false, period: 1, startDate: '', count: 0, times: [] }
    }
    weekdays.MONDAY = { on: true, period: 1, startDate: '2026-09-28', count: 2, times: [] }
    weekdays.WEDNESDAY = { on: true, period: 2, startDate: '2026-09-30', count: 1, times: [] }
    const r = slotRangeFromSlot({ mode: 'weekly', weekdays })
    expect(r.dateFrom).toBe('2026-09-28')
    expect(r.dateTo).toBe('2026-10-21')
  })
  test('weekly: cap 120 дней', () => {
    const weekdays = {}
    for (const d of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
      weekdays[d] = { on: false, period: 1, startDate: '', count: 0, times: [] }
    }
    weekdays.MONDAY = { on: true, period: 1, startDate: '2020-09-28', count: 500, times: [] }
    const r = slotRangeFromSlot({ mode: 'weekly', weekdays })
    expect(r.dateFrom).toBe('2020-09-28')
    expect(r.dateTo).toBe('2021-01-26')
  })
  test('weekly без дней — null', () => {
    const weekdays = {}
    for (const d of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
      weekdays[d] = { on: false, period: 1, times: [] }
    }
    expect(slotRangeFromSlot({ mode: 'weekly', startDate: '2026-09-28', weekdays })).toBeNull()
  })
})

describe('generateWeeklyDates', () => {
  const wd = (onDay) => {
    const weekdays = {}
    for (const d of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
      weekdays[d] = { on: d === onDay, period: 1, times: [] }
    }
    return weekdays
  }
  test('понедельники от startDate', () => {
    expect(generateWeeklyDates({ weekdays: wd('MONDAY'), startDate: '2026-09-28' }).slice(0, 3)).toEqual([
      '2026-09-28',
      '2026-10-05',
      '2026-10-12',
    ])
  })
  test('период раз в 2 недели', () => {
    const weekdays = wd('WEDNESDAY')
    weekdays.WEDNESDAY.period = 2
    expect(generateWeeklyDates({ weekdays, startDate: '2026-09-30' }).slice(0, 2)).toEqual([
      '2026-09-30',
      '2026-10-14',
    ])
  })
  test('cap по умолчанию 62', () => {
    expect(generateWeeklyDates({ weekdays: wd('MONDAY'), startDate: '2026-09-28' })).toHaveLength(62)
  })
  test('без startDate и дней — пусто', () => {
    expect(generateWeeklyDates({ weekdays: wd('MONDAY'), startDate: '' })).toEqual([])
    expect(generateWeeklyDates({ weekdays: {}, startDate: '2026-09-28' })).toEqual([])
  })
})

describe('fmtDur', () => {
  test('минуты и часы', () => {
    expect(fmtDur(45)).toBe('45 мин')
    expect(fmtDur(60)).toBe('1 ч')
    expect(fmtDur(90)).toBe('1 ч 30 мин')
  })
})

describe('lessonLinksVisible', () => {
  const START = new Date('2026-10-12T10:00').getTime()
  test('выключено и без конфигурации — всегда видны', () => {
    expect(lessonLinksVisible(null, '2026-10-12T10:00', START - 3600000)).toBe(true)
    expect(lessonLinksVisible({ link_visibility_enabled: false, link_lead_time_minutes: 15 }, '2026-10-12T10:00', START - 3600000)).toBe(true)
  })
  test('включено: скрыто раньше, видно с lead', () => {
    const cfg = { link_visibility_enabled: true, link_lead_time_minutes: 15 }
    expect(lessonLinksVisible(cfg, '2026-10-12T10:00', START - 16 * 60000)).toBe(false)
    expect(lessonLinksVisible(cfg, '2026-10-12T10:00', START - 15 * 60000)).toBe(true)
    expect(lessonLinksVisible(cfg, '2026-10-12T10:00', START)).toBe(true)
  })
  test('lead 0: видны с начала урока', () => {
    const cfg = { link_visibility_enabled: true, link_lead_time_minutes: 0 }
    expect(lessonLinksVisible(cfg, '2026-10-12T10:00', START - 60000)).toBe(false)
    expect(lessonLinksVisible(cfg, '2026-10-12T10:00', START)).toBe(true)
  })
  test('остаток минут', () => {
    const cfg = { link_visibility_enabled: true, link_lead_time_minutes: 15 }
    expect(lessonLinksRemainingMin(cfg, '2026-10-12T10:00', START - 16 * 60000)).toBe(1)
    expect(lessonLinksRemainingMin(cfg, '2026-10-12T10:00', START - 15 * 60000)).toBe(0)
    expect(lessonLinksRemainingMin({ link_visibility_enabled: false }, '2026-10-12T10:00', 0)).toBe(0)
  })
})

describe('resolveTutorColor', () => {
  const tutors = [{ tutor_user_id: 2 }, { tutor_user_id: 5 }, { tutor_user_id: 9 }]
  test('по порядку без выбора', () => {
    expect(resolveTutorColor(2, tutors, {})).toBe('c1')
    expect(resolveTutorColor(5, tutors, {})).toBe('c2')
    expect(resolveTutorColor(9, tutors, {})).toBe('c3')
  })
  test('ручной выбор побеждает', () => {
    expect(resolveTutorColor(5, tutors, { 5: 'c6' })).toBe('c6')
    expect(resolveTutorColor(2, tutors, { 5: 'c6' })).toBe('c1')
  })
  test('битый выбор и чужой id — детерминированный фолбэк', () => {
    expect(resolveTutorColor(5, tutors, { 5: 'cx' })).toBe('c2')
    expect(resolveTutorColor(99, tutors, {})).toBe('c1')
  })
})

describe('buildStudentPreview', () => {
  const NOW = new Date('2026-09-20T00:00').getTime()
  const ws = [{ start: '2026-09-28T09:00:00', end: '2026-09-28T11:30:00' }]
  test('dates: готовая строка валидна', () => {
    const { items, skippedPast } = buildStudentPreview(
      {
        mode: 'dates',
        dates: [{ date: '2026-09-28', times: [{ start: '10:00', end: '11:00' }] }],
        dropped: [],
      },
      ws,
      60,
      NOW,
    )
    expect(skippedPast).toBe(0)
    expect(items).toHaveLength(1)
    expect(items[0]).toMatchObject({ start: '2026-09-28T10:00', end: '2026-09-28T11:00', ok: true })
  })
  test('dates: прошлое пропускается', () => {
    const { items, skippedPast } = buildStudentPreview(
      {
        mode: 'dates',
        dates: [{ date: '2026-09-01', times: [{ start: '10:00', end: '11:00' }] }],
        dropped: [],
      },
      ws,
      60,
      NOW,
    )
    expect(items).toHaveLength(0)
    expect(skippedPast).toBe(1)
  })
  test('weekly: развёртка по дням со своими датами', () => {
    const weekdays = {}
    for (const d of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
      weekdays[d] = { on: false, period: 1, startDate: '', count: 0, times: [] }
    }
    weekdays.MONDAY = {
      on: true,
      period: 1,
      startDate: '2026-09-28',
      count: 2,
      times: [{ key: 1, start: '09:00', durationMin: null, durationKind: 'window' }],
    }
    const ws2 = [...ws, { start: '2026-10-05T09:00:00', end: '2026-10-05T11:30:00' }]
    const { items } = buildStudentPreview({ mode: 'weekly', weekdays, dropped: [] }, ws2, 60, NOW)
    expect(items).toHaveLength(2)
    expect(items[0]).toMatchObject({ start: '2026-09-28T09:00', end: '2026-09-28T11:30', ok: true })
    expect(items[1]).toMatchObject({ start: '2026-10-05T09:00', end: '2026-10-05T11:30', ok: true })
  })
  test('weekly: вне окна — invalid outside, не больше 10', () => {
    const weekdays = {}
    for (const d of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
      weekdays[d] = { on: false, period: 1, startDate: '', count: 0, times: [] }
    }
    weekdays.TUESDAY = {
      on: true,
      period: 1,
      startDate: '2026-09-28',
      count: 1,
      times: [{ key: 1, start: '09:00', durationMin: 60, durationKind: 'step' }],
    }
    const { items } = buildStudentPreview({ mode: 'weekly', weekdays, dropped: [] }, ws, 60, NOW)
    expect(items).toHaveLength(10)
    expect(items.every((x) => !x.ok && x.reason === 'outside')).toBe(true)
  })
})
