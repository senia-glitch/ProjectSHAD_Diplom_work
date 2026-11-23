import { describe, it, expect } from 'vitest'
import { buildPreview, fpOf, previewItems, hasSlotInput, fmtPreview, periodWord, validTime } from './preview.js'

// Среда 23.09.2026 08:00 — фиксированное "сейчас" для детерминизма.
const NOW = new Date('2026-09-23T08:00').getTime()

function fullWeekdays() {
  const weekdays = {}
  for (const id of ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']) {
    weekdays[id] = { on: false, period: 1, times: [] }
  }
  return weekdays
}

function datesSlot() {
  return {
    mode: 'dates',
    dates: [],
    weekdays: fullWeekdays(),
    startDate: '',
    count: 4,
    dropped: [],
    _fp: '',
  }
}

function weeklySlot() {
  return { mode: 'weekly', dates: [], weekdays: fullWeekdays(), dropped: [], _fp: '' }
}

describe('buildPreview: режим по дате', () => {
  it('собирает уроки из дат и времён, прошлое пропускает со счётчиком', () => {
    const slot = datesSlot()
    slot.dates = [
      { key: 1, date: '2026-09-24', times: [{ key: 1, start: '09:00', end: '10:00' }] },
      { key: 2, date: '2026-09-22', times: [{ key: 2, start: '09:00', end: '10:00' }] },
      { key: 3, date: '2026-09-24', times: [{ key: 3, start: '10:00', end: '09:00' }] },
    ]
    const { items, skippedPast } = buildPreview(slot, NOW)
    expect(items.map((i) => i.start)).toEqual(['2026-09-24T09:00'])
    expect(skippedPast).toBe(1)
  })
})

describe('buildPreview: режим по дням', () => {
  it('считает от недели даты дня: Ср раз в 3 → 23.09, 14.10, 04.11', () => {
    const slot = weeklySlot()
    slot.weekdays.WEDNESDAY.on = true
    slot.weekdays.WEDNESDAY.period = 3
    slot.weekdays.WEDNESDAY.startDate = '2026-09-23'
    slot.weekdays.WEDNESDAY.count = 3
    slot.weekdays.WEDNESDAY.times.push({ key: 1, start: '09:00', end: '10:00' })
    const { items, skippedPast } = buildPreview(slot, NOW)
    expect(items.map((i) => i.start)).toEqual(['2026-09-23T09:00', '2026-10-14T09:00', '2026-11-04T09:00'])
    expect(skippedPast).toBe(0)
  })

  it('первая неделя целиком, но прошлое всё равно пропускается', () => {
    const slot = weeklySlot()
    slot.weekdays.MONDAY.on = true
    slot.weekdays.MONDAY.startDate = '2026-09-23'
    slot.weekdays.MONDAY.count = 3
    slot.weekdays.MONDAY.times.push({ key: 1, start: '09:00', end: '10:00' })
    const { items, skippedPast } = buildPreview(slot, NOW)
    expect(items.map((i) => i.start)).toEqual(['2026-09-28T09:00', '2026-10-05T09:00', '2026-10-12T09:00'])
    expect(skippedPast).toBe(1)
  })

  it('у каждого дня своё кол-во: Пн×1 + Ср×2 → 3 урока', () => {
    const slot = weeklySlot()
    slot.weekdays.MONDAY.on = true
    slot.weekdays.MONDAY.startDate = '2026-09-23'
    slot.weekdays.MONDAY.count = 1
    slot.weekdays.MONDAY.times.push({ key: 1, start: '09:00', end: '10:00' })
    slot.weekdays.WEDNESDAY.on = true
    slot.weekdays.WEDNESDAY.startDate = '2026-09-23'
    slot.weekdays.WEDNESDAY.count = 2
    slot.weekdays.WEDNESDAY.times.push({ key: 2, start: '11:00', end: '12:00' })
    const { items } = buildPreview(slot, NOW)
    expect(items.map((i) => i.start)).toEqual(['2026-09-23T11:00', '2026-09-28T09:00', '2026-09-30T11:00'])
  })

  it('без дней и без даты — пусто', () => {
    expect(buildPreview(weeklySlot(), NOW).items).toEqual([])
    const noDate = weeklySlot()
    noDate.weekdays.MONDAY.on = true
    noDate.weekdays.MONDAY.count = 2
    expect(buildPreview(noDate, NOW).items).toEqual([])
  })
})

describe('previewItems / fpOf', () => {
  it('ручные удаления применяются, смена настроек их забывает', () => {
    const slot = datesSlot()
    slot.dates = [
      { key: 1, date: '2026-09-24', times: [{ key: 1, start: '09:00', end: '10:00' }] },
      { key: 2, date: '2026-09-25', times: [{ key: 2, start: '09:00', end: '10:00' }] },
    ]
    expect(previewItems(slot, NOW)).toHaveLength(2)
    const first = previewItems(slot, NOW)[0]
    slot.dropped = [first.key]
    expect(previewItems(slot, NOW)).toHaveLength(1)
    expect(fpOf(slot)).toContain('2026-09-24')
  })

  it('hasSlotInput различает пустую и заполненную форму', () => {
    expect(hasSlotInput(datesSlot())).toBe(false)
    const s = datesSlot()
    s.dates.push({ key: 1, date: '', times: [] })
    expect(hasSlotInput(s)).toBe(true)
  })
})

describe('periodWord / fmtPreview / validTime', () => {
  it('склоняет недели и форматирует строку', () => {
    expect(periodWord(1)).toBe('неделю')
    expect(periodWord(3)).toBe('недели')
    expect(periodWord(5)).toBe('недель')
    expect(fmtPreview('2026-09-24T09:00', '2026-09-24T10:00')).toBe('24.09 Чт 09:00–10:00')
    expect(validTime({ start: '09:00', end: '10:00' })).toBe(true)
    expect(validTime({ start: '10:00', end: '09:00' })).toBe(false)
  })
})
