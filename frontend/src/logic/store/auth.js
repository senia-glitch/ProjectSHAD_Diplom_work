// Состояние сессии. Только состояние и синхронные мутации:
// сеть — в actions/auth, токен в запросы подставляет api/.
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({ accessToken: null, refreshToken: null, user: null }),
  getters: {
    isLoggedIn: (s) => s.accessToken != null,
    role: (s) => s.user?.role || '',
    userName: (s) => s.user?.full_name || s.user?.username || '',
  },
  actions: {
    setSession({ accessToken, refreshToken, user }) {
      this.accessToken = accessToken ?? null
      this.refreshToken = refreshToken ?? null
      this.user = user ?? null
    },
    setTokens({ accessToken, refreshToken }) {
      if (accessToken !== undefined) this.accessToken = accessToken
      if (refreshToken !== undefined) this.refreshToken = refreshToken
    },
    setUser(user) {
      this.user = user ?? null
    },
    clearSession() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
    },
  },
})
