import { describe, it, expect } from 'vitest'
import { hasOverlap, blockGeometry } from './bookings.js'

const LIST = [
  { id: 1, weekday: 'MONDAY', start_time: '09:00', end_time: '10:00' },
  { id: 2, weekday: 'TUESDAY', start_time: '09:00', end_time: '10:00' },
]

describe('hasOverlap', () => {
  it('находит пересечение в тот же день', () => {
    expect(hasOverlap(LIST, 'MONDAY', '09:30', '10:30')).toBe(true)
    expect(hasOverlap(LIST, 'MONDAY', '10:00', '11:00')).toBe(false)
    expect(hasOverlap(LIST, 'WEDNESDAY', '09:30', '10:30')).toBe(false)
  })

  it('исключает бронь по id (редактирование самой себя)', () => {
    expect(hasOverlap(LIST, 'MONDAY', '09:30', '10:30', 1)).toBe(false)
  })
})

describe('blockGeometry', () => {
  it('считает позицию и минимальную высоту', () => {
    expect(blockGeometry('09:00', '10:00', 600)).toEqual({ top: '225px', height: '25px' })
    expect(blockGeometry('09:00', '09:05', 600).height).toBe('18px')
  })
})
