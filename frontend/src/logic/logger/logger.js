// Сквозная инфраструктура логов: перехват fetch/кликов/ошибок + батчинг.
// Отдельный модуль (не actions/): это не пользовательский сценарий.
// Работает с DOM/window осознанно: логгер — пограничная инфраструктура,
// а не логика предметной области; браузерных API вне этого модуля нет.
// Транспорт — logic/api/logs. 401 здесь НЕ обрабатывается:
// сессии — забота api/client + actions/auth.
import { postLogs } from '../api/index.js'

const FLUSH_INTERVAL = 2000
const BATCH_SIZE = 50
const LOG_ENDPOINT = '/api/v1/logs'

let buffer = []
let timer = null
let disabled = false
let initialized = false

function now() {
  return new Date().toISOString()
}

function push(entry) {
  if (disabled) return
  buffer.push(entry)
  if (buffer.length >= BATCH_SIZE) flush()
  if (!timer) timer = setTimeout(flush, FLUSH_INTERVAL)
}

function flush() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
  if (!buffer.length) return
  const batch = buffer.splice(0, buffer.length)
  postLogs(batch)
}

export function log(lvl, cat, msg, data) {
  push({ ts: now(), lvl, cat, msg, data: data ?? undefined })
}

export function logInfo(cat, msg, data) {
  log('info', cat, msg, data)
}
export function logWarn(cat, msg, data) {
  log('warn', cat, msg, data)
}
export function logError(cat, msg, data) {
  log('error', cat, msg, data)
}

function maskSensitive(key, val) {
  if (key === 'password' || key === 'password_hash' || key === 'access_token' || key === 'refresh_token') {
    return typeof val === 'string' ? '***' : val
  }
  return val
}

function maskBody(body) {
  if (typeof body === 'object' && body !== null) {
    const masked = { ...body }
    for (const key of Object.keys(masked)) {
      masked[key] = maskSensitive(key, masked[key])
    }
    return masked
  }
  return body
}

export function installLogger() {
  if (typeof window === 'undefined' || initialized) return
  initialized = true

  window.addEventListener('beforeunload', () => flush())

  window.addEventListener('error', (event) => {
    const err = event?.error
    logError('error', `JS Error: ${event?.message}`, {
      src: event?.filename,
      line: event?.lineno,
      col: event?.colno,
      stack: err?.stack,
    })
  })
  window.addEventListener('unhandledrejection', (e) => {
    logError('error', 'Unhandled Promise', {
      reason: String(e.reason?.message || e.reason),
      stack: e.reason?.stack,
    })
  })

  installFetchInterceptor()
  installClickLogger()
  installRouterLogger()
}

function isLogRequest(url) {
  return typeof url === 'string' && url.includes(LOG_ENDPOINT)
}

function installFetchInterceptor() {
  const origFetch = window.fetch
  window.fetch = async function (...args) {
    const [resource, init] = args
    const url = typeof resource === 'string' ? resource : resource?.url || ''

    if (!isLogRequest(url)) {
      const method = init?.method || 'GET'
      let reqBody = null
      if (init?.body) {
        try {
          reqBody = JSON.parse(init.body)
        } catch {
          reqBody = String(init.body).slice(0, 500)
        }
      }
      logInfo('api', `→ ${method} ${url}`, { body: reqBody ? maskBody(reqBody) : undefined })
    }

    try {
      const res = await origFetch.apply(this, args)

      if (!isLogRequest(url)) {
        const method = init?.method || 'GET'
        const clone = res.clone()
        let resBody = null
        try {
          resBody = await clone.json()
        } catch {
          try {
            resBody = await clone.text()
          } catch {
            // Тело не читается — логируем только статус.
          }
        }
        const logData = { status: res.status }
        if (resBody !== null && resBody !== undefined) {
          logData.res = typeof resBody === 'string' ? resBody.slice(0, 2000) : maskBody(resBody)
        }
        if (res.status >= 400) {
          logError('api', `← ${method} ${url} → ${res.status}`, logData)
        } else {
          logInfo('api', `← ${method} ${url} → ${res.status}`, logData)
        }
      }
      return res
    } catch (err) {
      if (!isLogRequest(url)) {
        const method = init?.method || 'GET'
        logError('api', `← ${method} ${url} → NETWORK ERROR`, { error: err.message })
      }
      throw err
    }
  }
}

function installClickLogger() {
  document.addEventListener(
    'click',
    (e) => {
      const el = e.target.closest('button') || e.target.closest('a') || e.target.closest('select')
      if (!el) return
      const tag = el.tagName.toLowerCase()
      const text = (el.textContent || '').trim().slice(0, 50)
      logInfo('ui', `click:${tag}`, { text })
    },
    true,
  )
}

function installRouterLogger() {
  let lastPath = location.pathname
  window.addEventListener('popstate', () => {
    if (location.pathname !== lastPath) {
      logInfo('nav', `${lastPath} → ${location.pathname}`)
      lastPath = location.pathname
    }
  })
}

export function logForm(form, name) {
  logInfo('form', `submit:${name}`, { data: { ...form } })
}

export function logState(cat, msg, data) {
  logInfo('state', msg, data)
}

export function disable() {
  disabled = true
}
export function enable() {
  disabled = false
}
