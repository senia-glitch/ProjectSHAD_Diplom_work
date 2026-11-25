// Личный чат: диалоги, сообщения открытых диалогов, непрочитанные, состояние соединения.
import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', {
  state: () => ({
    dialogs: [],
    threads: {}, // partnerId → { items, hasMore, loaded }
    unreadTotal: 0,
    connected: false,
    openPartner: null,
  }),
  actions: {
    setDialogs(items, unreadTotal) {
      this.dialogs = items
      this.unreadTotal = unreadTotal ?? items.reduce((n, d) => n + (d.unread || 0), 0)
    },
    setUnread(count) { this.unreadTotal = count },
    thread(partnerId) {
      if (!this.threads[partnerId]) this.threads[partnerId] = { items: [], hasMore: false, loaded: false }
      return this.threads[partnerId]
    },
    addMessage(partnerId, message) {
      const t = this.thread(partnerId)
      if (t.items.some((m) => m.id === message.id)) return false
      t.items.push(message)
      t.items.sort((a, b) => a.id - b.id)
      return true
    },
  },
})
