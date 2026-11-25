// Тонкий читатель сессии: реактивные геттеры store + восстановление.
// Сеть — только через actions/restoreSession.
import { computed } from 'vue'
import { useAuthStore } from '../../logic/store/index.js'
import { restoreSession } from '../../logic/actions/index.js'

export function useUser() {
  const store = useAuthStore()
  return {
    role: computed(() => store.role),
    isLoggedIn: computed(() => store.isLoggedIn),
    userName: computed(() => store.userName),
    userId: computed(() => store.user?.user_id ?? null),
    userAvatar: computed(() => store.user?.avatar_url || ''),
    fetchUser: () => restoreSession(),
  }
}
