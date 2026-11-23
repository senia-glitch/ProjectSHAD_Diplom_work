<template>
  <div v-if="dynLoading && !yearLessons.length" class="stack">
    <div class="skel skel--chart"></div>
    <div class="skel skel--chart"></div>
  </div>
  <div v-else-if="dynError && !yearLessons.length" class="state-box">
    <p>Не удалось загрузить. <button type="button" class="btn btn--sm btn--gry" @click="fetchYear()">Повторить</button></p>
  </div>
  <div v-else class="stack">
    <YearMatrix
      v-if="filters.dynMode === 'year'"
      :year="filters.year" :grid="grid" :metric="filters.dynMetric"
      :max-value="maxValue" :selected-day="selectedDay" :selected-month="selectedMonth"
      @pick-day="pickDay" @pick-month="pickMonth" @pick-year="pickYear"
    />
    <WeekCards
      v-else
      :year="filters.year" :weeks="weeks" :selected-key="selectedWeekKey" :busy-keys="busyWeekKeys"
      @pick-week="pickWeek"
    />
    <div v-if="dynError" class="state-box state-box--warn">
      <p>Список не обновлён: {{ dynError }}</p>
    </div>
    <div v-if="reportLoading" class="state-box">
      <p>Готовим отчёт...</p>
    </div>
    <div v-if="reportError" class="state-box state-box--warn">
      <p>{{ reportError }}</p>
    </div>
    <ReportBlock
      v-else-if="reportAgg"
      title="Отчёт репетитора"
      :range-label="reportRangeLabel"
      :agg="reportAgg"
      :rows="reportRows"
      :file-suffix="reportFileSuffix"
    />
  </div>
</template>

<script setup>
// Динамика: таблица Год 12x31 / карточки недель + блок «Информация-отчёт».
// Источник — детали уроков (бэк не меняем): год грузим целиком,
// день/месяц считаем из него, неделю догружаем точным диапазоном.
import { ref, computed, watch, onMounted } from 'vue'
import YearMatrix from './YearMatrix.vue'
import WeekCards from './WeekCards.vue'
import ReportBlock from './ReportBlock.vue'
import { useStatisticsPage } from './useStatisticsPage.js'
import { loadLessonDetailsFull } from '../../../logic/actions/index.js'
import {
  pivotYear, matrixMax, monthShort, monthRangeOf, isoWeeksOfYear,
  linesInRange, aggregateReport, daysBetweenInclusive,
} from '../../../logic/utils/index.js'
import { logError } from '../../../logic/logger/index.js'

const { filters } = useStatisticsPage()

const yearLessons = ref([])
const yearCancelCounts = ref({ byStudent: 0, byTutor: 0 })
const dynLoading = ref(false)
const dynError = ref('')
let seq = 0

// Контекст отчёта: день / неделя / месяц / год.
const reportSel = ref({ kind: 'year' })
const reportLessons = ref([])
const reportCancelCounts = ref({ byStudent: 0, byTutor: 0 })
const reportLoading = ref(false)
const reportError = ref('')
let rseq = 0

const selectedDay = computed(() => (reportSel.value.kind === 'day' ? reportSel.value.day : ''))
const selectedMonth = computed(() => (reportSel.value.kind === 'month' ? reportSel.value.month : -1))

const grid = computed(() => pivotYear(yearLessons.value, filters.year))
const maxValue = computed(() => matrixMax(grid.value, filters.dynMetric))
const weeks = computed(() => isoWeeksOfYear(filters.year))
const selectedWeekKey = computed(() => (reportSel.value.kind === 'week' ? reportSel.value.key : ''))
// Недели с уроками — по годовым деталям: урок попадает в неделю по дате.
const busyWeekKeys = computed(() => {
  const dates = new Set((yearLessons.value || []).map((l) => l.date))
  const busy = new Set()
  for (const w of weeks.value) {
    for (const d of dates) {
      if (d >= w.from && d <= w.to) {
        busy.add(w.key)
        break
      }
    }
  }
  return busy
})

function selRange() {
  const s = reportSel.value
  if (s.kind === 'day') return [s.day, s.day]
  if (s.kind === 'week') return [s.from, s.to]
  if (s.kind === 'month') {
    const r = monthRangeOf(`${filters.year}-${String(s.month + 1).padStart(2, '0')}`)
    return r || [`${filters.year}-01-01`, `${filters.year}-12-31`]
  }
  return [`${filters.year}-01-01`, `${filters.year}-12-31`]
}

const reportRangeLabel = computed(() => {
  const s = reportSel.value
  const fmt = (iso) => iso.split('-').reverse().join('.')
  if (s.kind === 'day') return `день ${fmt(s.day)}`
  if (s.kind === 'week') return `неделя ${s.week}: ${fmt(s.from)} – ${fmt(s.to)}`
  if (s.kind === 'month') return `месяц: ${monthShort(s.month)} ${filters.year}`
  return `год ${filters.year}`
})

const reportFileSuffix = computed(() => {
  const s = reportSel.value
  if (s.kind === 'day') return s.day
  if (s.kind === 'week') return `${s.from}_${s.to}`
  if (s.kind === 'month') return `${filters.year}-${String(s.month + 1).padStart(2, '0')}`
  return String(filters.year)
})

const reportRows = computed(() => {
  const [from, to] = selRange()
  return linesInRange(reportLessons.value, from, to)
})

const reportAgg = computed(() => {
  if (!reportLessons.value.length && reportSel.value.kind !== 'year') return null
  const [from, to] = selRange()
  const inRange = reportLessons.value.filter((l) => l.date >= from && l.date <= to)
  return aggregateReport(inRange, linesInRange(inRange, from, to), daysBetweenInclusive(from, to), reportCancelCounts.value)
})

async function fetchYear() {
  const my = ++seq
  dynLoading.value = true
  dynError.value = ''
  try {
    const year = filters.year || new Date().getFullYear()
    const full = await loadLessonDetailsFull({
      dateFrom: `${year}-01-01`,
      dateTo: `${year}-12-31`,
      studentIds: filters.studentIds,
    })
    if (my !== seq) return
    yearLessons.value = full.lessons
    yearCancelCounts.value = { byStudent: full.cancelledByStudent, byTutor: full.cancelledByTutor }
    if (reportSel.value.kind === 'year') {
      reportLessons.value = full.lessons
      reportCancelCounts.value = { ...yearCancelCounts.value }
    }
  } catch (e) {
    if (my !== seq) return
    dynError.value = e.status ? 'Не удалось загрузить уроки года' : 'Ошибка сети'
    logError('statistics', 'dynamics:error', { error: e.message })
  } finally {
    if (my === seq) dynLoading.value = false
  }
}

async function fetchReportRange() {
  const s = reportSel.value
  if (s.kind === 'year') {
    reportLessons.value = yearLessons.value
    reportCancelCounts.value = { ...yearCancelCounts.value }
    return
  }
  const [from, to] = selRange()
  const my = ++rseq
  reportLoading.value = true
  reportError.value = ''
  try {
    const full = await loadLessonDetailsFull({ dateFrom: from, dateTo: to, studentIds: filters.studentIds })
    if (my !== rseq) return
    reportLessons.value = full.lessons
    reportCancelCounts.value = { byStudent: full.cancelledByStudent, byTutor: full.cancelledByTutor }
  } catch (e) {
    if (my !== rseq) return
    logError('statistics', 'report:error', { error: e.message })
    // Не подменяем молча чужими данными: пустой отчёт + честный варнинг.
    reportLessons.value = []
    reportCancelCounts.value = { byStudent: 0, byTutor: 0 }
    reportError.value = e.status ? 'Не удалось загрузить отчёт' : 'Ошибка сети'
  } finally {
    if (my === rseq) reportLoading.value = false
  }
}

function pickDay(day) {
  reportSel.value = { kind: 'day', day }
}

function pickMonth(month) {
  reportSel.value = { kind: 'month', month }
}

function pickYear() {
  reportSel.value = { kind: 'year' }
}

function pickWeek(w) {
  reportSel.value = { kind: 'week', key: w.key, week: w.week, from: w.from, to: w.to }
}

watch(reportSel, fetchReportRange)

// Смена режима таблицы гасит контекстный отчёт: день/неделя другой матрицы
// к новой неприменимы.
watch(() => filters.dynMode, () => {
  reportSel.value = { kind: 'year' }
})

watch(
  [() => filters.year, () => [...filters.studentIds]],
  () => {
    reportSel.value = { kind: 'year' }
    fetchYear()
  },
)

onMounted(fetchYear)
</script>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 16px; }
.state-box {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg); padding: 28px 20px; text-align: center;
  color: var(--color-gray-600); font-size: 14px;
  display: flex; flex-direction: column; gap: 6px; align-items: center;
}
.state-box p { margin: 0; }
.state-box--warn { padding: 12px 16px; }
.skel {
  border-radius: var(--radius-lg); background: var(--color-gray-100);
  animation: skel-pulse 1.2s ease-in-out infinite;
}
.skel--chart { height: 300px; }
@keyframes skel-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}
</style>
