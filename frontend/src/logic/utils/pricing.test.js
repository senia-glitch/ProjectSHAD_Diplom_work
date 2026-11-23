import { describe, it, expect } from 'vitest'
import { finalPrice, discountAmount } from './pricing.js'

describe('finalPrice', () => {
  it('считает итог со скидкой', () => {
    expect(finalPrice(1000, 40)).toBe(600)
    expect(finalPrice(1000, 0)).toBe(1000)
    expect(finalPrice(999, 10)).toBe(899)
  })
})

describe('discountAmount', () => {
  it('считает размер скидки', () => {
    expect(discountAmount(1000, 40)).toBe(400)
    expect(discountAmount(1000, 0)).toBe(0)
  })
})
