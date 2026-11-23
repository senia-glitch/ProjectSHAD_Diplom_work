// Состояние страницы системной статистики: опрос раз в REFRESH_MS.
import { ref, onMounted, onUnmounted } from 'vue'
import { loadSystemStats, loadServerTime } from '../../../../logic/actions/index.js'

const REFRESH_MS = 5000

export function useSystemStatsPage() {
  const stats = ref(null)
  const serverTime = ref(null)
  const loading = ref(true)
  const error = ref('')
  let timer = 0

  async function refresh() {
    try {
      stats.value = await loadSystemStats()
      error.value = ''
    } catch (e) {
      error.value = e.message || 'Не удалось загрузить метрики'
    }
  }

  async function loadAll() {
    loading.value = true
    await Promise.all([
      refresh(),
      loadServerTime()
        .then((d) => { serverTime.value = d?.datetime ?? null })
        .catch(() => { serverTime.value = null }),
    ])
    loading.value = false
  }

  onMounted(() => {
    loadAll()
    timer = setInterval(refresh, REFRESH_MS)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { stats, serverTime, loading, error, reload: loadAll }
}
