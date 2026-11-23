import { ref } from 'vue'

const theme = ref(typeof document !== 'undefined' && document.documentElement.dataset.theme === 'light' ? 'light' : 'dark')

export function useTheme() {
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = theme.value
    try { localStorage.setItem('shad-theme', theme.value) } catch { /* Storage may be disabled. */ }
  }
  return { theme, toggleTheme }
}
