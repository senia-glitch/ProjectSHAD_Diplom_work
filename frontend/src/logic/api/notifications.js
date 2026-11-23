import { apiFetch, withQuery } from './client.js'

export function getNotifications({ limit = 30, offset = 0 } = {}) {
  return apiFetch(withQuery('/api/v1/notifications', { limit, offset }))
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
