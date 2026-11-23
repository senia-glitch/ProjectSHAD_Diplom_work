import { onMounted, onUnmounted } from 'vue'

// Закрытие модального окна/панели по Escape.
// isOpen — функция, возвращающая текущее состояние; onClose — действие закрытия.
export function useEscapeKey(isOpen, onClose) {
  function onKeydown(e) {
    if (e.key !== 'Escape' || e.defaultPrevented || !isOpen()) return
    e.preventDefault()
    onClose()
  }
  onMounted(() => document.addEventListener('keydown', onKeydown))
  onUnmounted(() => document.removeEventListener('keydown', onKeydown))
  return { onKeydown }
}
