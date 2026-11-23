import { defineStore } from 'pinia'

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    items: [],
    unreadCount: 0,
  }),
  actions: {
    setNotifications(items) {
      this.items = items
    },
    setUnreadCount(count) {
      this.unreadCount = count
    },
    markRead(id) {
      const item = this.items.find((x) => x.id === id)
      if (item && !item.read) {
        item.read = true
        this.unreadCount = Math.max(0, this.unreadCount - 1)
        return true
      }
      return false
    },
    markUnread(id) {
      const item = this.items.find((x) => x.id === id)
      if (item && item.read) {
        item.read = false
        this.unreadCount += 1
      }
    },
    markAllRead() {
      for (const item of this.items) item.read = true
      this.unreadCount = 0
    },
    appendNotifications(items) {
      this.items = [...this.items, ...items]
    },
    clear() {
      this.items = []
      this.unreadCount = 0
    },
  },
})
