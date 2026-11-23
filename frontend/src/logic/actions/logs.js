// Сценарий страницы журнала: чтение логов с фильтрами.
import { getLogs } from '../api/index.js'

export async function loadLogs(filters = {}) {
  const data = await getLogs(filters)
  return { items: data.items || [], total: data.total || 0 }
}
