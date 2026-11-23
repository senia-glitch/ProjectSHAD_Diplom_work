// Администрирование.
import { apiFetch, withQuery } from './client.js'

export function listAdminUsers({ limit, offset } = {}) {
  return apiFetch(withQuery('/api/v1/admin/users', { limit, offset }))
}

export function getAdminUser(userId) {
  return apiFetch(`/api/v1/admin/users/${userId}`)
}

export function patchAdminUser(userId, patch) {
  return apiFetch(`/api/v1/admin/users/${userId}`, { method: 'PATCH', body: patch })
}
