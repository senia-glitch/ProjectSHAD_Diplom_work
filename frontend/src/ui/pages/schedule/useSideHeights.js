// Замер центральной колонки для капа боковых: ряд не растягивается
// их содержимым. DOM-узел приходит событием grid-ready от ScheduleGrid.
import { ref, computed, onUnmounted } from 'vue'

export function useSideHeights() {
  const sideMaxH = ref(null)
  const colStyle = computed(() => (sideMaxH.value ? { maxHeight: sideMaxH.value } : null))
  let sideRo = null

  function syncSideHeights(el) {
    if (el) sideMaxH.value = `${el.clientHeight}px`
  }

  function bindGridBox(el) {
    if (!el) return
    sideRo?.disconnect()
    syncSideHeights(el)
    sideRo = new ResizeObserver(() => syncSideHeights(el))
    sideRo.observe(el)
  }

  onUnmounted(() => sideRo?.disconnect())

  return { colStyle, bindGridBox }
}
