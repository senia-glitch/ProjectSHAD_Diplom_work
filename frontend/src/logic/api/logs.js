// Журнал фронтенд-логов: запись пачки и чтение с фильтрами.
import { apiFetch, withQuery } from './client.js'

export async function postLogs(batch) {
  try {
    await apiFetch('/api/v1/logs', {
      method: 'POST',
      body: { logs: batch },
      auth: true,
      retry: false,
    })
  } catch {
    // Потеря пачки логов — не ошибка приложения.
  }
}

export function getLogs({ lvl, cat, date, q, limit = 100, offset = 0 } = {}) {
  return apiFetch(
    withQuery('/api/v1/logs', { lvl, cat, date, q, limit, offset }),
  )
}
