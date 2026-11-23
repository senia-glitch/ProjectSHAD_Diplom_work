// Состояние страницы статистики: общий фильтр в store (один на все вкладки),
// загрузка aggregates и деталей уроков. Ключ хранения — shad.statistics.v2.
import { ref, computed, watch, onMounted } from 'vue'
import {
  loadTutorStatistics, loadTutorStudents, loadMyProfile, loadStatisticsLessons,
} from '../../../logic/actions/index.js'
import { useStatisticsStore, useRosterStore } from '../../../logic/store/index.js'
import { resolveRequestRange, toISODate } from '../../../logic/utils/index.js'
import { STORAGE_KEYS } from '../../../logic/constants/index.js'
import { logError } from '../../../logic/logger/index.js'

const STORAGE_KEY = STORAGE_KEYS.statisticsFilters
let filtersReady = false
let initSuspended = false

function readStoredFilters(fallback) {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (typeof saved !== 'object' || !saved) return { ...fallback }
    const out = { ...fallback }
    if (Number.isInteger(saved.year) && saved.year >= 2000 && saved.year <= 2100) out.year = saved.year
    if (['year', 'month', 'week', 'custom'].includes(saved.preset)) out.preset = saved.preset
    if (['year', 'week'].includes(saved.dynMode)) out.dynMode = saved.dynMode
    if (typeof saved.dynMetric === 'string') out.dynMetric = saved.dynMetric
    if (typeof saved.month === 'string') out.month = saved.month
    if (typeof saved.weekAnchor === 'string') out.weekAnchor = saved.weekAnchor
    if (typeof saved.customFrom === 'string') out.customFrom = saved.customFrom
    if (typeof saved.customTo === 'string') out.customTo = saved.customTo
    if (Array.isArray(saved.studentIds)) out.studentIds = saved.studentIds.filter(Number.isInteger)
    return out
  } catch {
    return { ...fallback }
  }
}

export function useStatisticsPage({ root = false } = {}) {
  const now = new Date()
  const thisYear = now.getFullYear()
  const statsStore = useStatisticsStore()
  const rosterStore = useRosterStore()

  const loading = ref(false)
  const error = ref('')
  const tutorName = ref('')
  const today = toISODate(new Date())
  const filters = statsStore.filters

  const years = computed(() => [thisYear - 3, thisYear - 2, thisYear - 1, thisYear, thisYear + 1])
  const students = computed(() => rosterStore.students || [])
  const data = computed(() => statsStore.data)
  const lessons = computed(() => statsStore.lessons)
  const lessonsLoading = computed(() => statsStore.lessonsLoading)
  const lessonsError = computed(() => statsStore.lessonsError)

  const dateRange = computed(() => {
    const r = resolveRequestRange(filters)
    return [r.dateFrom, r.dateTo]
  })

  function saveFilters() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        year: filters.year,
        preset: filters.preset,
        month: filters.month,
        weekAnchor: filters.weekAnchor,
        customFrom: filters.customFrom,
        customTo: filters.customTo,
        studentIds: filters.studentIds,
        dynMode: filters.dynMode,
        dynMetric: filters.dynMetric,
      }))
    } catch {
      // Приватный режим и т.п. — страница работает и без сохранения.
    }
  }

  function setFilters(patch) {
    statsStore.setFilters(patch)
  }

  function resetFilters() {
    // Полный сброс страницы: фильтры + вид уроков + «в отчёт».
    statsStore.resetLessonsView()
    statsStore.resetReportInclude()
    statsStore.setFilters({
      year: thisYear,
      preset: 'year',
      month: `${thisYear}-${String(now.getMonth() + 1).padStart(2, '0')}`,
      weekAnchor: toISODate(now),
      customFrom: `${thisYear}-01-01`,
      customTo: toISODate(now),
      granularity: 'auto',
      studentIds: [],
      dynMode: 'year',
      dynMetric: 'conducted',
    })
  }

  async function reload() {
    loading.value = true
    error.value = ''
    statsStore.clearStatistics()
    try {
      // Год берём из разрешённого диапазона, а не из селектора:
      // иначе якорь недели/месяц из другого года давал бы 422.
      const r = resolveRequestRange(filters)
      await loadTutorStatistics({
        year: r.year,
        dateFrom: r.dateFrom,
        dateTo: r.dateTo,
        granularity: filters.granularity === 'auto' ? undefined : filters.granularity,
        studentIds: filters.studentIds,
      })
    } catch (e) {
      error.value = e.status
        ? e.payload?.error?.message || e.message || 'Не удалось загрузить статистику'
        : 'Ошибка сети'
      logError('statistics', 'reload:error', { error: e.message })
    } finally {
      loading.value = false
    }
  }

  async function reloadLessons() {
    try {
      await loadStatisticsLessons({
        dateFrom: dateRange.value[0],
        dateTo: dateRange.value[1],
        studentIds: filters.studentIds,
      })
    } catch (e) {
      logError('statistics', 'reloadLessons:error', { error: e.message })
    }
  }

  function toggleStudent(id) {
    const list = filters.studentIds.includes(id)
      ? filters.studentIds.filter((x) => x !== id)
      : [...filters.studentIds, id]
    setFilters({ studentIds: list })
  }

  function selectAllStudents() {
    setFilters({ studentIds: [] })
  }

  function selectStudent(id) {
    setFilters({ studentIds: [id] })
  }

  // Инициализация один раз на страницу: фильтр из хранилища, ростер, имя.
  // Вотчер на время инициализации приостановлен, иначе фильтр из localStorage
  // и валидация учеников вызывали бы по лишней перезагрузке каждый.
  async function initOnce() {
    initSuspended = true
    try {
      if (!filtersReady) {
        filtersReady = true
        const fallback = {
          year: thisYear,
          preset: 'year',
          month: `${thisYear}-${String(now.getMonth() + 1).padStart(2, '0')}`,
          weekAnchor: toISODate(now),
          customFrom: `${thisYear}-01-01`,
          customTo: toISODate(now),
          granularity: 'auto',
          studentIds: [],
          dynMode: 'year',
          dynMetric: 'conducted',
        }
        setFilters(readStoredFilters(fallback))
      }
      try {
        await loadTutorStudents()
        const known = new Set((rosterStore.students || []).map((s) => s.student_id))
        setFilters({ studentIds: filters.studentIds.filter((id) => known.has(id)) })
      } catch (e) {
        logError('statistics', 'roster:error', { error: e.message })
      }
      try {
        const me = await loadMyProfile()
        tutorName.value = me?.full_name || me?.username || ''
      } catch (e) {
        logError('statistics', 'profile:error', { error: e.message })
      }
    } finally {
      initSuspended = false
    }
    await reload()
  }

  // Ключи, меняющие серверные данные вкладок Уроки/Ученики.
  // dynMode/dynMetric сюда не входят: динамика строится на клиенте
  // из годовых деталей и не требует перезагрузки.
  const DATA_KEYS = ['year', 'preset', 'month', 'weekAnchor', 'customFrom', 'customTo', 'studentIds', 'granularity']
  const dataKey = () => JSON.stringify(DATA_KEYS.map((k) => filters[k]))

  // Вотчер и инициализация — только у корневой обёртки,
  // иначе каждая вкладка плодила бы свои перезагрузки.
  if (root) {
    watch(filters, () => {
      if (initSuspended) return
      saveFilters()
    }, { deep: true })
    watch(dataKey, () => {
      if (initSuspended) return
      reload()
    })
    onMounted(initOnce)
  }

  return {
    loading, error, today, tutorName, filters, years, students,
    data, lessons, lessonsLoading, lessonsError,
    dateRange,
    reload, reloadLessons, toggleStudent, selectAllStudents, selectStudent,
    setFilters, resetFilters,
  }
}
