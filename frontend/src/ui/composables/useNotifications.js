import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNotificationsStore, useAuthStore } from '../../logic/store/index.js'
import { loadNotifications, loadUnreadNotificationsCount, markRead } from '../../logic/actions/index.js'

export function useNotifications() {
  const store = useNotificationsStore()
  const authStore = useAuthStore()
  const panelOpen = ref(false)
  const loading = ref(false)
  let timer = 0

  async function refreshUnread() {
    if (!authStore.isLoggedIn) return
    try {
      await loadUnreadNotificationsCount()
    } catch {
      return
    }
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

  function onHoverItem(item) {
    if (item && !item.read) markRead(item.id)
  }

  onMounted(() => {
    refreshUnread()
    timer = setInterval(refreshUnread, 30000)
    document.addEventListener('click', onDocClick)
    window.addEventListener('resize', onResize)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
    document.removeEventListener('click', onDocClick)
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
