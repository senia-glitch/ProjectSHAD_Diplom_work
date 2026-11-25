// Вид навигации: «full» — разделы в шапке, страницы раздела в левом меню (только широкий экран);
// «minimal» — всё в верхнем меню, как раньше. Хранится в браузере; у репетитора совпадает
// с настройкой «Вид интерфейса» в его настройках.
import { computed, ref } from 'vue'

const KEY = 'shad-nav-mode'
export const NAV_MODES = [
  { value: 'full', label: 'Информативный', hint: 'Разделы — в верхнем меню, страницы раздела — в меню слева (на компьютере)' },
  { value: 'minimal', label: 'Минималистичный', hint: 'Всё в верхнем меню, разделы раскрываются списком' },
]
const WIDE_QUERY = '(min-width: 1100px)'

function readMode() {
  try { return localStorage.getItem(KEY) === 'minimal' ? 'minimal' : 'full' } catch { return 'full' }
}

const mode = ref(typeof window === 'undefined' ? 'full' : readMode())
const wide = ref(typeof window !== 'undefined' && !!window.matchMedia?.(WIDE_QUERY).matches)
if (typeof window !== 'undefined' && window.matchMedia) {
  window.matchMedia(WIDE_QUERY).addEventListener?.('change', (e) => { wide.value = e.matches })
}

export function setNavMode(value) {
  mode.value = value === 'minimal' ? 'minimal' : 'full'
  try { localStorage.setItem(KEY, mode.value) } catch { /* хранилище может быть отключено */ }
}

// Настройка репетитора на сервере → вид навигации в этом браузере.
export const navModeFromScheduleType = (type) => (type === 'MINIMALISTIC' ? 'minimal' : 'full')
export const scheduleTypeFromNavMode = (value) => (value === 'minimal' ? 'MINIMALISTIC' : 'INFORMATIVE')

export function useNavMode() {
  return {
    navMode: mode,
    // Левое меню показывается только на широком экране и в информативном виде.
    sidebarAllowed: computed(() => mode.value === 'full' && wide.value),
    setNavMode,
  }
}
