import { describe, it, expect } from 'vitest'
import { safeUrl } from './urls.js'

describe('safeUrl', () => {
  it('пропускает http/https', () => {
    expect(safeUrl('https://example.com/meet')).toBe('https://example.com/meet')
    expect(safeUrl('http://localhost:8000/x')).toBe('http://localhost:8000/x')
    expect(safeUrl('  HTTPS://EXAMPLE.COM  ')).toBe('HTTPS://EXAMPLE.COM')
  })

  it('блокирует javascript:/data:/прочее', () => {
    expect(safeUrl('javascript:alert(1)')).toBeNull()
    expect(safeUrl('JaVaScRiPt:alert(1)')).toBeNull()
    expect(safeUrl('data:text/html,<h1>x</h1>')).toBeNull()
    expect(safeUrl('ftp://example.com/x')).toBeNull()
    expect(safeUrl('/relative/path')).toBeNull()
    expect(safeUrl('')).toBeNull()
    expect(safeUrl(null)).toBeNull()
    expect(safeUrl(undefined)).toBeNull()
    expect(safeUrl(123)).toBeNull()
  })
})
