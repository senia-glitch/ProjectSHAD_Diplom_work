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

// ----- Админ-панель владельца -----
const A = '/api/v1/admin'
export const fetchAdminDashboard = () => apiFetch(`${A}/dashboard`)
export const postRotateAdminKey = () => apiFetch(`${A}/key/rotate`, { method: 'POST' })
export const fetchAdminAudit = ({ action, limit, offset } = {}) => apiFetch(withQuery(`${A}/audit`, { action, limit, offset }))
export const postBlockUser = (userId, reason) => apiFetch(`${A}/users/${userId}/block`, { method: 'POST', body: { reason: reason || null } })
export const postUnblockUser = (userId) => apiFetch(`${A}/users/${userId}/unblock`, { method: 'POST' })
export const postResetPassword = (userId) => apiFetch(`${A}/users/${userId}/reset-password`, { method: 'POST' })
export const deleteAdminUser = (userId) => apiFetch(`${A}/users/${userId}`, { method: 'DELETE' })
export const fetchDbTables = () => apiFetch(`${A}/db/tables`)
export const fetchDbRows = (table, params) => apiFetch(withQuery(`${A}/db/tables/${encodeURIComponent(table)}`, params))
export const patchDbRow = (table, pk, values) => apiFetch(`${A}/db/tables/${encodeURIComponent(table)}/row`, { method: 'PATCH', body: { pk, values } })
export const deleteDbRow = (table, pk) => apiFetch(`${A}/db/tables/${encodeURIComponent(table)}/row/delete`, { method: 'POST', body: { pk } })
export const postDbSql = ({ sql, write = false, confirm = false }) => apiFetch(`${A}/db/sql`, { method: 'POST', body: { sql, write, confirm } })
