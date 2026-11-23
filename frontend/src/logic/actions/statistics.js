// Сценарии страницы статистики: загрузка aggregates с фильтрами.
import { getTutorStatistics, getTutorLessonDetails } from '../api/index.js'
import { useStatisticsStore } from '../store/index.js'
import { STORAGE_KEYS } from '../constants/index.js'

// Порядковые номера запросов: при быстрой смене фильтров устаревший
// ответ не должен затирать свежие данные в store.
let statsSeq = 0
let lessonsSeq = 0

// Инвалидация in-flight загрузок (например, при logout): просроченные
// ответы не должны записываться в store нового пользователя.
export function invalidateStatisticsLoads() {
  statsSeq += 1
  lessonsSeq += 1
}

export function clearStatisticsFilters() {
  try {
    localStorage.removeItem(STORAGE_KEYS.statisticsFilters)
  } catch {
    return
  }
}

export async function loadTutorStatistics(filters = {}) {
  const my = ++statsSeq
  const data = await getTutorStatistics(filters)
  if (my !== statsSeq) return data
  const store = useStatisticsStore()
  store.setStatistics(data)
  return data
}

export async function loadStatisticsLessons(filters = {}) {
  const my = ++lessonsSeq
  const store = useStatisticsStore()
  store.lessonsLoading = true
  store.lessonsError = ''
  try {
    const data = await getTutorLessonDetails(filters)
    if (my !== lessonsSeq) return store.lessons
    store.setLessons(data.lessons || [])
    return store.lessons
  } catch (e) {
    if (my !== lessonsSeq) throw e
    store.setLessons([])
    store.lessonsError = e.status
      ? e.payload?.error?.message || e.message || 'Не удалось загрузить уроки'
      : 'Ошибка сети'
    throw e
  } finally {
    if (my === lessonsSeq) store.lessonsLoading = false
  }
}
