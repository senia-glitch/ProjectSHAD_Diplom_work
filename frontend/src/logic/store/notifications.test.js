import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useNotificationsStore } from './notifications.js'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('notifications store', () => {
  it('markRead помечает элемент и уменьшает счётчик', () => {
    const store = useNotificationsStore()
    store.setNotifications([
      { id: 1, read: false, text: 'А' },
      { id: 2, read: true, text: 'Б' },
    ])
    store.setUnreadCount(1)
    expect(store.markRead(1)).toBe(true)
    expect(store.items[0].read).toBe(true)
    expect(store.unreadCount).toBe(0)
    expect(store.markRead(1)).toBe(false)
  })

  it('markUnread откатывает пометку при ошибке сети', () => {
    const store = useNotificationsStore()
    store.setNotifications([{ id: 1, read: false, text: 'А' }])
    store.setUnreadCount(1)
    store.markRead(1)
    store.markUnread(1)
    expect(store.items[0].read).toBe(false)
    expect(store.unreadCount).toBe(1)
  })

  it('clear сбрасывает список и счётчик', () => {
    const store = useNotificationsStore()
    store.setNotifications([{ id: 1, read: false, text: 'А' }])
    store.setUnreadCount(3)
    store.clear()
    expect(store.items).toEqual([])
    expect(store.unreadCount).toBe(0)
  })

  it('markAllRead помечает всё и обнуляет счётчик', () => {
    const store = useNotificationsStore()
    store.setNotifications([
      { id: 1, read: false, text: 'А' },
      { id: 2, read: false, text: 'Б' },
      { id: 3, read: true, text: 'В' },
    ])
    store.setUnreadCount(2)
    store.markAllRead()
    expect(store.items.every((i) => i.read)).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('appendNotifications дописывает страницу в конец', () => {
    const store = useNotificationsStore()
    store.setNotifications([{ id: 1, read: false, text: 'А' }])
    store.appendNotifications([
      { id: 2, read: false, text: 'Б' },
      { id: 3, read: true, text: 'В' },
    ])
    expect(store.items.map((i) => i.id)).toEqual([1, 2, 3])
  })
})
