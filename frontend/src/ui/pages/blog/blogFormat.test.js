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

import { commentThreads } from './blogFormat.js'

describe('commentThreads', () => {
  it('собирает ответы под исходным комментарием в порядке появления', () => {
    const threads = commentThreads([
      { id: 1, parent_id: null }, { id: 2, parent_id: null }, { id: 3, parent_id: 1 }, { id: 4, parent_id: 1 }, { id: 5, parent_id: 99 },
    ])
    expect(threads.map((t) => [t.root.id, t.replies.map((r) => r.id)])).toEqual([[1, [3, 4]], [2, []], [5, []]])
  })
})
