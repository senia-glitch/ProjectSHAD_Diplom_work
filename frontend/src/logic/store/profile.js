// Собственный профиль пользователя.
import { defineStore } from 'pinia'

export const useProfileStore = defineStore('profile', {
  state: () => ({ me: null }),
  actions: {
    setMe(me) {
      this.me = me ?? null
    },
  },
})
