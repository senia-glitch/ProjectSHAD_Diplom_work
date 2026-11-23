import { describe, it, expect } from 'vitest'
import { formatUptime, formatMs, formatQueueLoad } from './system.js'

describe('formatUptime', () => {
  it('часы и минуты с секундами', () => {
    expect(formatUptime(3661)).toBe('01:01:01')
  })

  it('больше суток — день и часы', () => {
    expect(formatUptime(90061)).toBe('1 д 01:01:01')
  })

  it('ноль и мусор — 00:00:00', () => {
    expect(formatUptime(0)).toBe('00:00:00')
    expect(formatUptime(undefined)).toBe('00:00:00')
  })
})

describe('formatMs', () => {
  it('меньше 10 — с десятыми', () => {
    expect(formatMs(2.34)).toBe('2.3 мс')
    expect(formatMs(9.96)).toBe('10.0 мс')
  })

  it('10 и выше — целые', () => {
    expect(formatMs(42.6)).toBe('43 мс')
    expect(formatMs(42.2)).toBe('42 мс')
  })

  it('NaN и мусор — 0', () => {
    expect(formatMs(undefined)).toBe('0.0 мс')
    expect(formatMs('abc')).toBe('0.0 мс')
  })
})

describe('formatQueueLoad', () => {
  it('очередь относительно пула в процентах', () => {
    expect(formatQueueLoad({ queue_size: 2, pool_size: 8 })).toBe('2 / 8 (25%)')
  })

  it('пул 0 — явная отметка', () => {
    expect(formatQueueLoad({ queue_size: 3, pool_size: 0 })).toBe('пул 0')
  })
})
