import { describe, it, expect } from 'vitest'
import { formatLogTs, logLevelClass, formatLogData } from './logs.js'

describe('formatLogTs', () => {
  it('ISO и «пробел» форматы (локальное время)', () => {
    expect(formatLogTs('2026-10-11T16:14:00')).toMatch(/11\.10\.2026, 16:14:00/)
    expect(formatLogTs('2026-10-11 16:14:00')).toMatch(/11\.10\.2026, 16:14:00/)
  })

  it('мусор не ломает', () => {
    expect(formatLogTs('')).toBe('')
    expect(formatLogTs(null)).toBe('')
  })
})

describe('logLevelClass', () => {
  it('класс по уровню', () => {
    expect(logLevelClass('error')).toBe('lvl lvl--error')
    expect(logLevelClass('ERROR')).toBe('lvl lvl--error')
    expect(logLevelClass('warn')).toBe('lvl lvl--warn')
    expect(logLevelClass('info')).toBe('lvl lvl--info')
    expect(logLevelClass('')).toBe('lvl lvl--info')
  })
})

describe('formatLogData', () => {
  it('компактный JSON', () => {
    expect(formatLogData({ status: 401 })).toBe('{"status":401}')
  })

  it('длинное режется с многоточием', () => {
    const out = formatLogData({ trace: 'x'.repeat(200) }, 50)
    expect(out.length).toBe(51)
    expect(out.endsWith('…')).toBe(true)
  })

  it('не-объекты дают пустую строку', () => {
    expect(formatLogData(null)).toBe('')
    expect(formatLogData('текст')).toBe('')
  })
})
