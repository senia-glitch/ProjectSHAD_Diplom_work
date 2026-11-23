<template>
  <div v-if="loading && !data" class="stack">
    <div class="skel skel--table"></div>
  </div>
  <div v-else-if="error && !data" class="state-box">
    <p>Не удалось загрузить. <button type="button" class="btn btn--sm btn--gry" @click="reload()">Повторить</button></p>
  </div>
  <div v-else-if="data && !data.by_student.length" class="state-box">
    <p><b>Учеников нет.</b></p>
    <p>Добавьте ученика по личному коду на странице «Ученики».</p>
  </div>
  <div v-else-if="data" class="stack">
    <StudentModeCard
      v-if="singleRow"
      :row="singleRow" :series="data.by_student_series"
      :buckets="(data.series || []).map((r) => r.bucket)"
      :granularity="data.meta.granularity"
    />
    <StudentTable
      v-else
      :rows="data.by_student"
      :debt-by-id="debtById" :period="`${dateRange[0]}_${dateRange[1]}`"
      @select="pickStudent"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import StudentModeCard from './StudentModeCard.vue'
import StudentTable from './StudentTable.vue'
import { useRouter } from 'vue-router'
import { useStatisticsPage } from './useStatisticsPage.js'
import { loadLessonDetails } from '../../../logic/actions/index.js'
import { logError } from '../../../logic/logger/index.js'

const {
  loading, error, filters, data, dateRange, selectStudent, reload,
} = useStatisticsPage()
const router = useRouter()

// Долг по ученикам: сумма неоплаченных проведённых записей за период.
// Оплата живёт в записи на урок (цена у каждого ученика своя),
// бэк не меняем — считаем на клиенте из деталей одним запросом.
const debtById = ref({})
let debtSeq = 0

async function fetchDebt() {
  if (!data.value || filters.studentIds.length === 1) {
    debtById.value = {}
    return
  }
  const my = ++debtSeq
  try {
    const lessons = await loadLessonDetails({
      dateFrom: dateRange.value[0],
      dateTo: dateRange.value[1],
      studentIds: filters.studentIds,
    })
    if (my !== debtSeq) return
    const debt = {}
    for (const l of lessons) {
      if (l.status !== 'FINISHED') continue
      for (const s of l.students || []) {
        if (!s.paid) debt[s.student_id] = (debt[s.student_id] || 0) + (s.amount || 0)
      }
    }
    debtById.value = debt
  } catch (e) {
    if (my !== debtSeq) return
    logError('statistics', 'debt:error', { error: e.message })
  }
}

watch([dateRange, () => filters.studentIds, data], fetchDebt, { deep: true })
onMounted(fetchDebt)

const singleRow = computed(() => {
  if (filters.studentIds.length !== 1 || !data.value) return null
  return data.value.by_student.find((r) => r.student_id === filters.studentIds[0]) || null
})

function pickStudent(row) {
  selectStudent(row.student_id)
  router.push('/statistics/overview')
}
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
.skel {
  border-radius: var(--radius-lg); background: var(--color-gray-100);
  animation: skel-pulse 1.2s ease-in-out infinite;
}
.skel--table { height: 220px; }
@keyframes skel-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}
</style>
