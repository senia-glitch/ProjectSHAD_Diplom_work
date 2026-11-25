// Личный чат: история и запасная отправка (основной канал — WebSocket в logic/actions/chat.js).
import { apiFetch, withQuery } from './client.js'
import { toUserTime } from '../utils/tz.js'

const V1 = '/api/v1/chat'
// Время с сервера (UTC) — в поясе пользователя, как во всём приложении.
export const chatMessageToUser = (m) => ({ ...m, created_at: toUserTime(m.created_at), read_at: m.read_at ? toUserTime(m.read_at) : null })
const dialogToUser = (d) => ({ ...d, last_at: d.last_at ? toUserTime(d.last_at) : null })

export async function fetchChatDialogs() {
  const data = await apiFetch(`${V1}/dialogs`)
  return { ...data, items: (data.items || []).map(dialogToUser) }
}
export async function fetchBoardChatDialogs(boardId) {
  const data = await apiFetch(`${V1}/board/${encodeURIComponent(boardId)}/dialogs`)
  return { ...data, items: (data.items || []).map(dialogToUser) }
}
export const fetchChatUnread = () => apiFetch(`${V1}/unread`)
export async function fetchChatMessages(partnerId, { beforeId, limit } = {}) {
  const data = await apiFetch(withQuery(`${V1}/dialogs/${partnerId}/messages`, { before_id: beforeId, limit }))
  return { ...data, items: (data.items || []).map(chatMessageToUser) }
}
export const postChatMessage = (partnerId, text) => apiFetch(`${V1}/dialogs/${partnerId}/messages`, { method: 'POST', body: { text } })
export const postChatRead = (partnerId) => apiFetch(`${V1}/dialogs/${partnerId}/read`, { method: 'POST' })
