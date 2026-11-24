import { describe, expect, it } from 'vitest'
import { commentsWord, formatDate, initials } from './blogFormat.js'

describe('blogFormat', () => {
  it('склоняет «комментарий» по числу', () => {
    expect([0, 1, 2, 5, 11, 21, 22, 112].map(commentsWord)).toEqual([
      'комментариев', 'комментарий', 'комментария', 'комментариев',
      'комментариев', 'комментарий', 'комментария', 'комментариев',
    ])
  })

  it('берёт первую букву имени для аватара', () => {
    expect(initials(' анна ')).toBe('А')
    expect(initials('')).toBe('?')
    expect(initials(null)).toBe('?')
  })

  it('не падает на пустой дате', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate('2026-11-24T10:00:00Z')).toMatch(/2026/)
  })
})
