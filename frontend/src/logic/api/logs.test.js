import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { postLogs } from './logs.js'
import { registerTokenProvider, registerRefreshHandler, registerUnauthorizedHandler } from './client.js'

describe('protected background log delivery', () => {
  let refresh
  let unauthorized

  beforeEach(() => {
    refresh = vi.fn()
    unauthorized = vi.fn()
    registerTokenProvider(() => null)
    registerRefreshHandler(refresh)
    registerUnauthorizedHandler(unauthorized)
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => vi.unstubAllGlobals())

  it('does not send guest logs to a protected endpoint', async () => {
    await postLogs([{ lvl: 'info', msg: 'guest navigation' }])
    expect(fetch).not.toHaveBeenCalled()
    expect(unauthorized).not.toHaveBeenCalled()
  })

  it('a log 401 neither clears nor refreshes the user session', async () => {
    registerTokenProvider(() => 'expired-access')
    fetch.mockResolvedValue({ status: 401, ok: false, json: async () => ({}) })
    await postLogs([{ lvl: 'info', msg: 'background telemetry' }])
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(refresh).not.toHaveBeenCalled()
    expect(unauthorized).not.toHaveBeenCalled()
  })

  it('preserves authenticated log delivery and the batch contract', async () => {
    registerTokenProvider(() => 'valid-access')
    fetch.mockResolvedValue({ status: 200, ok: true, json: async () => ({ ok: true }) })
    const batch = [{ lvl: 'info', msg: 'authenticated navigation' }]
    await postLogs(batch)
    expect(fetch).toHaveBeenCalledWith('/api/v1/logs', expect.objectContaining({
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer valid-access' },
      body: JSON.stringify({ logs: batch }),
    }))
  })
})
