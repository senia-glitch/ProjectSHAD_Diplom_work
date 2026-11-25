// Личный чат: одно WebSocket-соединение на вкладку, переподключение, запасная отправка по REST.
import {
  chatMessageToUser, fetchBoardChatDialogs, fetchChatDialogs, fetchChatMessages, fetchChatUnread, postChatMessage, postChatRead,
} from '../api/index.js'
import { useAuthStore, useChatStore } from '../store/index.js'
import { refreshSession } from './auth.js'

let socket = null
let retryTimer = 0
let pingTimer = 0
let attempt = 0
let wanted = false
let refreshed = false
let cidSeq = 0
const pending = new Map() // cid → { resolve, reject, timer }
const listeners = new Set()

// Подписка страниц на входящие события (например, отметить прочитанным открытый диалог).
export function onChatEvent(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

const partnerOf = (message, me) => (message.sender_id === me ? (message.sender_id === message.tutor_user_id ? message.student_user_id : message.tutor_user_id) : message.sender_id)

function handle(msg) {
  const store = useChatStore()
  const me = useAuthStore().user?.user_id
  if (msg.t === 'ready') {
    attempt = 0
    refreshed = false
    store.connected = true
  } else if (msg.t === 'message') {
    const message = chatMessageToUser(msg.message)
    const partner = partnerOf(message, me)
    store.addMessage(partner, message)
    const dialog = store.dialogs.find((d) => d.partner_id === partner)
    const incoming = message.sender_id !== me
    if (dialog) {
      Object.assign(dialog, { last_text: message.text.slice(0, 140), last_at: message.created_at, last_from_me: !incoming })
      if (incoming && store.openPartner !== partner) dialog.unread += 1
      store.dialogs.sort((a, b) => String(b.last_at || '').localeCompare(String(a.last_at || '')))
    }
    if (incoming && store.openPartner !== partner) store.unreadTotal += 1
  } else if (msg.t === 'sent' || msg.t === 'error') {
    const p = pending.get(msg.cid)
    if (p) {
      clearTimeout(p.timer)
      pending.delete(msg.cid)
      if (msg.t === 'sent') p.resolve(msg.id)
      else p.reject(new Error(msg.message || 'Не удалось отправить сообщение'))
    }
  } else if (msg.t === 'read') {
    // Собеседник прочитал мои сообщения.
    const thread = store.threads[msg.by]
    if (thread) for (const m of thread.items) if (m.sender_id === me && !m.read_at) m.read_at = new Date().toISOString()
  } else if (msg.t === 'read_self') {
    const dialog = store.dialogs.find((d) => d.partner_id === msg.partner_id)
    if (dialog && dialog.unread) {
      store.unreadTotal = Math.max(0, store.unreadTotal - dialog.unread)
      dialog.unread = 0
    }
  }
  for (const fn of listeners) fn(msg)
}

function scheduleReconnect() {
  if (!wanted) return
  clearTimeout(retryTimer)
  const delay = Math.min(15000, 600 * 2 ** attempt) + Math.random() * 400
  attempt += 1
  retryTimer = setTimeout(open, delay)
}

function open() {
  if (!wanted || socket) return
  const token = useAuthStore().accessToken
  if (!token) return
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${proto}//${location.host}/api/v1/chat/ws`)
  socket = ws
  ws.addEventListener('open', () => ws.send(JSON.stringify({ t: 'hello', token })))
  ws.addEventListener('message', (e) => {
    try { handle(JSON.parse(e.data)) } catch { /* битое сообщение пропускаем */ }
  })
  ws.addEventListener('close', async (e) => {
    if (socket === ws) socket = null
    useChatStore().connected = false
    clearInterval(pingTimer)
    for (const [cid, p] of pending) { clearTimeout(p.timer); p.reject(new Error('Нет связи с сервером')); pending.delete(cid) }
    if (!wanted) return
    if (e.code === 4403 && !refreshed) {
      refreshed = true // сессия могла истечь: один повтор с обновлённым токеном
      if (await refreshSession()) { open(); return }
    }
    scheduleReconnect()
  })
  clearInterval(pingTimer)
  pingTimer = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send('{"t":"ping"}') }, 25000)
}

export function connectChat() {
  wanted = true
  if (!socket) open()
}

export function disconnectChat() {
  wanted = false
  clearTimeout(retryTimer)
  clearInterval(pingTimer)
  if (socket) { try { socket.close(1000) } catch { /* уже закрыт */ } }
  socket = null
}

export async function loadChatDialogs() {
  const data = await fetchChatDialogs()
  useChatStore().setDialogs(data.items, data.unread_total)
  return data.items
}

export const loadBoardChatDialogs = async (boardId) => (await fetchBoardChatDialogs(boardId)).items

export async function loadChatUnread() {
  const data = await fetchChatUnread()
  useChatStore().setUnread(data.count)
  return data.count
}

export async function loadChatThread(partnerId, { older = false } = {}) {
  const store = useChatStore()
  const thread = store.thread(partnerId)
  const beforeId = older && thread.items.length ? thread.items[0].id : undefined
  const data = await fetchChatMessages(partnerId, { beforeId })
  for (const m of data.items) store.addMessage(partnerId, m)
  thread.hasMore = data.has_more
  thread.loaded = true
  return thread
}

// Открытый диалог: входящие в нём сразу прочитаны, счётчики снимаются.
export async function markChatRead(partnerId) {
  const store = useChatStore()
  const dialog = store.dialogs.find((d) => d.partner_id === partnerId)
  if (dialog?.unread) {
    store.unreadTotal = Math.max(0, store.unreadTotal - dialog.unread)
    dialog.unread = 0
  }
  if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ t: 'read', with: partnerId }))
  else await postChatRead(partnerId).catch(() => {})
}

export function setOpenChat(partnerId) {
  useChatStore().openPartner = partnerId
}

// Отправка: по WebSocket с подтверждением, без соединения — через REST (сообщение придёт событием).
export function sendChatMessage(partnerId, text) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    const cid = `c${++cidSeq}`
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(cid); reject(new Error('Сервер не ответил, попробуйте ещё раз')) }, 10000)
      pending.set(cid, { resolve, reject, timer })
      socket.send(JSON.stringify({ t: 'send', cid, to: partnerId, text }))
    })
  }
  return postChatMessage(partnerId, text).then((res) => {
    const store = useChatStore()
    store.addMessage(partnerId, chatMessageToUser(res.message))
    return res.message.id
  })
}

export function resetChat() {
  disconnectChat()
  useChatStore().$reset()
}
