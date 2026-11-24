// Узкий экран (телефон): реактивный флаг по медиазапросу.
// На телефоне сетки расписания и броней показывают 3 дня вместо недели.
import { ref, onMounted, onBeforeUnmount } from 'vue'

export const NARROW_QUERY = '(max-width: 720px)'
export const NARROW_DAYS = 3

export function useNarrowScreen(query = NARROW_QUERY) {
  const media = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query) : null
  const narrow = ref(Boolean(media?.matches))
  const update = (e) => { narrow.value = e.matches }
  onMounted(() => media?.addEventListener?.('change', update))
  onBeforeUnmount(() => media?.removeEventListener?.('change', update))
  return narrow
}
