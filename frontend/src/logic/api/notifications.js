import { apiFetch, withQuery } from './client.js'
import { toUserTime } from '../utils/tz.js'

export async function getNotifications({ limit = 30, offset = 0 } = {}) {
  const data = await apiFetch(withQuery('/api/v1/notifications', { limit, offset }))
  // Время создания — UTC с сервера; показываем в поясе пользователя.
  return data
    ? { ...data, notifications: (data.notifications || []).map((n) => ({ ...n, created_at: toUserTime(n.created_at) })) }
    : data
}

export function getUnreadNotificationsCount() {
  return apiFetch('/api/v1/notifications/unread-count')
}

export function markNotificationRead(id) {
  return apiFetch(`/api/v1/notifications/${id}/read`, { method: 'POST' })
}

export function markAllNotificationsRead() {
  return apiFetch('/api/v1/notifications/read-all', { method: 'POST' })
}
