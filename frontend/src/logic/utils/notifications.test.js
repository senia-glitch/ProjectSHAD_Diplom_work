import { describe, it, expect } from 'vitest'
import { groupNotificationsByDay, formatNotifTime } from './notifications.js'

const NOW = new Date(2030, 5, 12, 15, 0) // 12.06.2030 15:00

function item(id, created_at, read = false) {
  return { id, created_at, read, text: `Т${id}` }
}

describe('groupNotificationsByDay', () => {
  it('сгруппирует по дням и подпишет сегодня/вчера', () => {
    const items = [
      item(1, '2030-06-12T10:00:00'),
      item(2, '2030-06-11T23:30:00'),
      item(3, '2030-06-11T08:00:00'),
      item(4, '2030-06-10T08:00:00'),
    ]
    const groups = groupNotificationsByDay(items, NOW)
    expect(groups.map((g) => g.label)).toEqual(['Сегодня', 'Вчера', '10.06.2030'])
    expect(groups[0].items.map((i) => i.id)).toEqual([1])
    expect(groups[1].items.map((i) => i.id)).toEqual([2, 3])
    expect(groups[2].items.map((i) => i.id)).toEqual([4])
  })

  it('сохраняет порядок элементов внутри дня', () => {
    const items = [
      item(1, '2030-06-12T09:00:00'),
      item(2, '2030-06-12T11:00:00'),
    ]
    const groups = groupNotificationsByDay(items, NOW)
    expect(groups).toHaveLength(1)
    expect(groups[0].items.map((i) => i.id)).toEqual([1, 2])
  })

  it('непаравимую дату кладёт в отдельную группу', () => {
    const groups = groupNotificationsByDay([item(1, 'не дата')], NOW)
    expect(groups).toHaveLength(1)
    expect(groups[0].items[0].id).toBe(1)
  })

  it('пустой список — пустой результат', () => {
    expect(groupNotificationsByDay([], NOW)).toEqual([])
  })
})

describe('formatNotifTime', () => {
  it('форматирует ISO и «пробел» форматы', () => {
    expect(formatNotifTime('2030-06-12T10:00:00')).toMatch(/12\.06\.2030/)
    expect(formatNotifTime('2030-06-12 10:00:00')).toMatch(/12\.06\.2030/)
  })

  it('непаравимое значение возвращает как есть', () => {
    expect(formatNotifTime('—')).toBe('—')
    expect(formatNotifTime(null)).toBe('')
  })
})
