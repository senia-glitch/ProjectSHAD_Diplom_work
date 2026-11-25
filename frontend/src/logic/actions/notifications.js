import { getNotifications, getUnreadNotificationsCount, markNotificationRead, markAllNotificationsRead } from '../api/index.js'
import { useNotificationsStore } from '../store/index.js'

export async function loadNotifications(options = {}) {
  const data = await getNotifications(options)
  const store = useNotificationsStore()
  store.setNotifications(data.notifications || [])
  store.setUnreadCount(data.unread_count ?? 0)
  return data
}

export async function loadMoreNotifications(options = {}) {
  const store = useNotificationsStore()
  const data = await getNotifications({ ...options, offset: store.items.length })
  store.appendNotifications(data.notifications || [])
  store.setUnreadCount(data.unread_count ?? store.unreadCount)
  return data
}

export async function loadUnreadNotificationsCount() {
  const data = await getUnreadNotificationsCount()
  useNotificationsStore().setUnreadCount(data.count ?? 0)
  return data
}

export async function markRead(id) {
  const store = useNotificationsStore()
  if (!store.markRead(id)) return
  try {
    await markNotificationRead(id)
  } catch {
    store.markUnread(id)
  }
}

export async function markAllRead() {
  await markAllNotificationsRead()
  useNotificationsStore().markAllRead()
}

// Свежие уведомления для всплывающего показа: store списка не трогаем.
export async function loadLatestNotifications(limit = 3) {
  const data = await getNotifications({ limit, offset: 0 })
  return data?.notifications || []
}
