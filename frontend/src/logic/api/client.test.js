// Single-flight refresh: параллельные 401 должны делить один refresh-запрос.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  apiFetch,
  registerTokenProvider,
  registerRefreshHandler,
  registerUnauthorizedHandler,
} from './client.js'

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

describe('apiFetch refresh single-flight', () => {
  beforeEach(() => {
    registerTokenProvider(() => 'old-token')
    registerRefreshHandler(() => Promise.resolve(null))
    registerUnauthorizedHandler(() => {})
  })

  it('параллельные 401 вызывают refresh ровно один раз', async () => {
    let refreshCalls = 0
    registerRefreshHandler(async () => {
      refreshCalls += 1
      await new Promise((r) => setTimeout(r, 10))
      return 'new-token'
    })
    globalThis.fetch = vi.fn(async (_url, init) => {
      const auth = init?.headers?.Authorization || ''
      if (auth === 'Bearer old-token') return jsonResponse(401, { error: { message: 'x' } })
      if (auth === 'Bearer new-token') return jsonResponse(200, { ok: true })
      return jsonResponse(403, {})
    })
    const results = await Promise.all([apiFetch('/a'), apiFetch('/b'), apiFetch('/c')])
    expect(refreshCalls).toBe(1)
    expect(results.every((r) => r.ok)).toBe(true)
  })

  it('провал refresh не ретраит и зовёт unauthorized-хендлер', async () => {
    let unauthorized = 0
    registerRefreshHandler(async () => null)
    registerUnauthorizedHandler(() => {
      unauthorized += 1
    })
    globalThis.fetch = vi.fn(async () => jsonResponse(401, { error: { message: 'x' } }))
    await expect(apiFetch('/a')).rejects.toMatchObject({ status: 401 })
    expect(unauthorized).toBe(1)
  })
})
