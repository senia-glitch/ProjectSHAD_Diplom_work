// Транспорт: единственный fetch-обёртка проекта.
// Токен берёт у провайдера (регистрирует actions/auth при bootstrap),
// api/ store не знает. Повтор после refresh — только один раз.
// Каждый вызов обёрнут в AbortController (timeout, по умолчанию 30000 мс);
// отмена превращается в ApiError со status 0 (сетевой сбой, не HTTP).
// Эндпойнты аутентификации ходят с { auth: false } — без ретраев.
import { translateErrorMessage } from './errors.js'

export class ApiError extends Error {
  constructor(status, message, payload) {
    super(message)
    this.status = status
    this.payload = payload
  }
}

let tokenProvider = null
let refreshHandler = null
let unauthorizedHandler = null
// Single-flight для refresh: параллельные 401 делят один refresh-запрос,
// чтобы ротация refresh-токена не разлогинивала пользователя.
let refreshPromise = null

export function registerTokenProvider(fn) {
  tokenProvider = fn
}
export function registerRefreshHandler(fn) {
  refreshHandler = fn
}
export function registerUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

export function withQuery(path, params) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== undefined && v !== null && v !== '') q.append(k, String(v))
  }
  const s = q.toString()
  return s ? `${path}?${s}` : path
}

function errorMessage(status, payload) {
  return translateErrorMessage(status, payload?.error?.message)
}

async function rawFetch(path, { method, body, token, signal }) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  return { res, data }
}

export async function apiFetch(path, opts = {}) {
  const { method = 'GET', body, auth = true, retry = true, timeout = 30000, optionalAuth = false } = opts
  const token = auth && tokenProvider ? tokenProvider() : null
  // Background telemetry requires an existing session; it must not clear or refresh it.
  if (optionalAuth && !token) return null
  const doCall = async (callToken) => {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), timeout)
    try {
      return await rawFetch(path, { method, body, token: callToken, signal: ctrl.signal })
    } catch (e) {
      if (e?.name === 'AbortError') {
        throw new ApiError(0, translateErrorMessage(0, 'Request timeout'), {
          error: { message: 'Request timeout' },
        })
      }
      // fetch отклоняется TypeError при недоступной сети/сервере.
      if (e instanceof TypeError) {
        throw new ApiError(0, translateErrorMessage(0, ''), { error: { message: e.message } })
      }
      throw e
    } finally {
      clearTimeout(timer)
    }
  }
  let result = await doCall(token)
  if (result.res.status === 401 && auth && retry && !optionalAuth && refreshHandler) {
    if (!refreshPromise) {
      refreshPromise = refreshHandler()
        .catch(() => null)
        .finally(() => {
          refreshPromise = null
        })
    }
    const fresh = await refreshPromise
    if (fresh) {
      result = await doCall(fresh)
    }
  }
  const { res, data } = result
  if (!res.ok) {
    if (res.status === 401 && auth && !optionalAuth && unauthorizedHandler) {
      try {
        await unauthorizedHandler()
      } catch {
        // Хендлер не должен ронять исходную ошибку.
      }
    }
    throw new ApiError(res.status, errorMessage(res.status, data), data)
  }
  return data
}
