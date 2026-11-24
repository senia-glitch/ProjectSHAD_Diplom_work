// Состояние страницы календаря: режим месяц/список, выбор дня, загрузка
// уроков за видимый месяц. Устаревшие ответы отбрасываются по счётчику.
import { ref, computed, watch, onMounted } from 'vue'
import { loadCalendarLessons } from '../../../logic/actions/index.js'
import {
  monthMatrix, monthRangeISO, shiftMonth, countByDay, dayLessons,
  userNowDate,
} from '../../../logic/utils/index.js'
import { logError } from '../../../logic/logger/index.js'

export function useCalendarPage() {
  const now = userNowDate()
  const year = ref(now.getFullYear())
  const month = ref(now.getMonth() + 1)
  const mode = ref('month')
  const selectedDay = ref('')

  const lessons = ref([])
  const loading = ref(false)
  const error = ref('')

  const counts = computed(() => countByDay(lessons.value))
  const weeks = computed(() => monthMatrix(year.value, month.value))
  const dayLessonsList = computed(() =>
    selectedDay.value ? dayLessons(lessons.value, selectedDay.value) : [])

  const monthLabel = computed(() =>
    new Date(year.value, month.value - 1, 1)
      .toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' }))

  let requestId = 0

  async function reload() {
    const my = ++requestId
    loading.value = true
    error.value = ''
    try {
      const [from, to] = monthRangeISO(year.value, month.value)
      const rows = await loadCalendarLessons({ dateFrom: from, dateTo: to })
      if (my !== requestId) return
      lessons.value = rows
    } catch (e) {
      if (my !== requestId) return
      error.value = e.payload?.error?.message || e.message || 'Не удалось загрузить календарь'
      logError('calendar', 'reload:error', { error: e.message })
    } finally {
      if (my === requestId) loading.value = false
    }
  }

  function shift(delta) {
    selectedDay.value = ''
    const next = shiftMonth(year.value, month.value, delta)
    year.value = next.year
    month.value = next.month
  }

  function goToday() {
    selectedDay.value = ''
    const d = userNowDate()
    year.value = d.getFullYear()
    month.value = d.getMonth() + 1
  }

  function pickDay(iso) {
    selectedDay.value = selectedDay.value === iso ? '' : iso
    if (selectedDay.value) mode.value = 'list'
  }

  function clearDay() {
    selectedDay.value = ''
  }

  watch([year, month], reload)
  onMounted(reload)

  return {
    year, month, mode, selectedDay,
    lessons, loading, error,
    monthLabel, counts, weeks, dayLessonsList,
    shift, goToday, pickDay, clearDay, reload,
  }
}
