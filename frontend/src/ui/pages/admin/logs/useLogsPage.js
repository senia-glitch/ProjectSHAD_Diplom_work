// Состояние страницы журнала: фильтры, страницы, автообновление.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { loadLogs } from '../../../../logic/actions/index.js'
import { logError } from '../../../../logic/logger/index.js'

const PAGE_SIZE = 100
const REFRESH_MS = 10000

export function useLogsPage() {
  const lvl = ref('')
  const cat = ref('')
  const date = ref('')
  const q = ref('')

  const items = ref([])
  const total = ref(0)
  const offset = ref(0)
  const loading = ref(false)
  const error = ref('')
  let timer = 0
  let requestId = 0

  const page = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
  const pages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
  const hasPrev = computed(() => offset.value > 0)
  const hasNext = computed(() => offset.value + PAGE_SIZE < total.value)

  async function reload() {
    const my = ++requestId
    loading.value = true
    error.value = ''
    try {
      const data = await loadLogs({
        lvl: lvl.value || undefined,
        cat: cat.value || undefined,
        date: date.value || undefined,
        q: q.value || undefined,
        limit: PAGE_SIZE,
        offset: offset.value,
      })
      if (my !== requestId) return
      items.value = data.items
      total.value = data.total
    } catch (e) {
      if (my !== requestId) return
      error.value = e.payload?.error?.message || e.message || 'Не удалось загрузить журнал'
      logError('logs', 'reload:error', { error: e.message })
    } finally {
      if (my === requestId) loading.value = false
    }
  }

  function goPrev() {
    if (hasPrev.value) {
      offset.value = Math.max(0, offset.value - PAGE_SIZE)
      reload()
    }
  }
  function goNext() {
    if (hasNext.value) {
      offset.value += PAGE_SIZE
      reload()
    }
  }
  function reset() {
    lvl.value = ''
    cat.value = ''
    date.value = ''
    q.value = ''
    offset.value = 0
    reload()
  }

  // Смена любого фильтра — сначала страница и перезагрузка.
  watch([lvl, cat, date, q], () => {
    offset.value = 0
    reload()
  })

  onMounted(() => {
    reload()
    timer = setInterval(reload, REFRESH_MS)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return {
    lvl, cat, date, q,
    items, total, loading, error,
    page, pages, hasPrev, hasNext,
    goPrev, goNext, reset,
  }
}
