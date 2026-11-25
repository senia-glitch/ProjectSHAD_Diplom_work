import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNotificationsStore, useAuthStore } from '../../logic/store/index.js'
import { loadNotifications, loadUnreadNotificationsCount, loadLatestNotifications, markRead } from '../../logic/actions/index.js'
import { toast } from '../legacy/testing/kit.js'

// Число непрочитанных во вкладке браузера: «(2) Расписание · SHAD».
function showUnreadInTitle(count) {
  const base = document.title.replace(/^\(\d+\) /, '')
  document.title = count > 0 ? `(${count}) ${base}` : base
}

// Последнее известное число непрочитанных в этой вкладке: рост — повод показать новое уведомление.
let knownUnread = null

export function useNotifications() {
  const store = useNotificationsStore()
  const authStore = useAuthStore()
  const panelOpen = ref(false)
  const loading = ref(false)
  let timer = 0

  async function refreshUnread() {
    if (!authStore.isLoggedIn) {
      knownUnread = null  // другой пользователь после входа не получит чужих «новых»
      return
    }
    try {
      await loadUnreadNotificationsCount()
    } catch {
      return
    }
    const count = store.unreadCount
    if (knownUnread !== null && count > knownUnread && !panelOpen.value) {
      try {
        const fresh = (await loadLatestNotifications(Math.min(3, count - knownUnread))).filter((n) => !n.read)
        for (const n of fresh.reverse()) toast(n.text, 'ok')
      } catch {
        // Всплывающий показ необязателен: число на колокольчике уже обновлено.
      }
    }
    knownUnread = count
    showUnreadInTitle(count)
  }

  function openPanel() {
    panelOpen.value = !panelOpen.value
    if (panelOpen.value && authStore.isLoggedIn) {
      loading.value = true
      loadNotifications()
        .catch(() => {})
        .finally(() => (loading.value = false))
    }
  }

  function closePanel() {
    panelOpen.value = false
  }

  function onDocClick(e) {
    if (!panelOpen.value) return
    if (e.target.closest('.notif-panel') || e.target.closest('.notif-area')) return
    closePanel()
  }

  function onResize() {
    closePanel()
  }

  function onKeydown(e) {
    if (e.key === 'Escape' && panelOpen.value) {
      closePanel()
      document.querySelector('.notif-bell')?.focus()
    }
  }

  function onHoverItem(item) {
    if (item && !item.read) markRead(item.id)
  }

  onMounted(() => {
    refreshUnread()
    timer = setInterval(refreshUnread, 30000)
    document.addEventListener('click', onDocClick)
    document.addEventListener('keydown', onKeydown)
    window.addEventListener('resize', onResize)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
    document.removeEventListener('click', onDocClick)
    document.removeEventListener('keydown', onKeydown)
    window.removeEventListener('resize', onResize)
  })

  return {
    items: computed(() => store.items),
    unreadCount: computed(() => store.unreadCount),
    panelOpen,
    loading,
    openPanel,
    closePanel,
    onHoverItem,
  }
}
