// Чат в оболочке страниц: соединение для вошедших репетитора и ученика, число непрочитанных.
import { computed, onMounted, watch } from 'vue'
import { useAuthStore, useChatStore } from '../../logic/store/index.js'
import { connectChat, loadChatUnread } from '../../logic/actions/index.js'

const CHAT_ROLES = ['tutor', 'student']

export function useChat() {
  const auth = useAuthStore()
  const store = useChatStore()
  const enabled = computed(() => auth.isLoggedIn && CHAT_ROLES.includes(auth.role))

  function start() {
    if (!enabled.value) return
    connectChat()
    loadChatUnread().catch(() => {})
  }
  onMounted(start)
  watch(enabled, (on) => { if (on) start() })

  return { chatEnabled: enabled, chatUnread: computed(() => store.unreadTotal) }
}
