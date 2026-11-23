<template>
  <div v-if="lessonsLoading && !lessons.length" class="skel skel--table"></div>
  <div v-else-if="lessonsError && !lessons.length" class="state-box">
    <p>Не удалось загрузить. <button type="button" class="btn btn--sm btn--gry" @click="reloadLessons">Повторить</button></p>
  </div>
  <template v-else>
    <div v-if="lessonsError" class="state-box state-box--err">
      <p>Список не обновлён: {{ lessonsError }}</p>
    </div>
    <LessonsList
      :lessons="filtered"
      empty-title="За период уроков нет"
      empty-hint="Под фильтры ничего не попало — смягчите статусы или тип."
      @toggle-pay="onTogglePay"
    />
    <p v-if="filtered.length" class="totals-line">
      Всего: {{ filtered.length }} ур. · {{ totalHours }} ч · {{ formatMoney(totalSum) }}
    </p>
  </template>

  <Teleport to="body">
    <div v-if="printPayload" class="print-sheet">
      <h1>{{ printPayload.title }}</h1>
      <p>{{ printPayload.subtitle }}</p>
      <table>
        <thead>
          <tr><th v-for="(h, i) in printPayload.head" :key="i">{{ h }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in printPayload.rows" :key="i">
            <td v-for="(c, j) in r" :key="j">{{ c }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="printPayload.foot" class="print-foot">{{ printPayload.foot }}</p>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import LessonsList from './LessonsList.vue'
import { useStatisticsPage } from './useStatisticsPage.js'
import { useStatisticsStore } from '../../../logic/store/index.js'
import { setParticipantPaid } from '../../../logic/actions/index.js'
import { logError } from '../../../logic/logger/index.js'
import { formatMoney, buildLessonsCsv, buildLessonsPrintData } from '../../../logic/utils/index.js'
import { downloadText, reportFileName } from './studentCsv.js'

const {
  dateRange, filters, lessons, lessonsLoading, lessonsError, reloadLessons, today, tutorName,
} = useStatisticsPage()
// Вид списка (статусы/тип) живёт в сторе: контролы — в сайдбаре.
const statsStore = useStatisticsStore()
const statuses = computed(() => statsStore.lessonsStatuses)
const typeFilter = computed(() => statsStore.lessonsType)
const printPayload = ref(null)

function matchStatus(l) {
  if (statuses.value.includes(l.status)) return true
  // Один чекбокс «Запланированные» покрывает SCHEDULED и ONGOING.
  if (l.status === 'ONGOING' && statuses.value.includes('SCHEDULED')) return true
  return false
}

watch([dateRange, () => filters.studentIds], () => reloadLessons(), { deep: true })
// Выгрузка из сайдбара: кнопки CSV/Печать живут в фильтрах, выполняет список.
watch(() => statsStore.lessonsExport.n, (n) => {
  if (!n) return
  if (statsStore.lessonsExport.kind === 'print') printList()
  else exportCsv()
})
onMounted(reloadLessons)

function cleanupPrint() {
  document.body.classList.remove('printing')
}

onMounted(() => window.addEventListener('afterprint', cleanupPrint))
onUnmounted(() => window.removeEventListener('afterprint', cleanupPrint))

const filtered = computed(() => lessons.value.filter((l) => {
  if (!matchStatus(l)) return false
  if (typeFilter.value === 'single' && l.is_group) return false
  if (typeFilter.value === 'group' && !l.is_group) return false
  return true
}))

const totalHours = computed(() => Math.round(filtered.value.reduce((s, l) => s + (l.minutes || 0), 0) / 60 * 100) / 100)
const totalSum = computed(() => filtered.value.reduce((s, l) => s + (l.total || 0), 0))

function periodPart() {
  return `${dateRange.value[0]}_${dateRange.value[1]}`
}

async function refreshAfterPay(promise) {
  try {
    await promise
  } catch (e) {
    logError('statistics', 'pay:error', { error: e.message })
  }
  await reloadLessons()
}

function onTogglePay({ lessonId, studentUserId, paid }) {
  return refreshAfterPay(setParticipantPaid(lessonId, studentUserId, paid))
}

function exportCsv() {
  const sid = filters.studentIds.length === 1 ? filters.studentIds[0] : null
  downloadText(reportFileName('uroki', periodPart(), sid), buildLessonsCsv(filtered.value))
}

async function printList() {
  printPayload.value = buildLessonsPrintData(
    filtered.value,
    'Уроки',
    `${tutorName.value ? `${tutorName.value} · ` : ''}${periodPart().replace('_', ' — ')} · выгружено ${today}`,
  )
  await nextTick()
  document.body.classList.add('printing')
  window.print()
}
</script>

<style scoped>
.state-box {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg); padding: 20px; text-align: center;
  color: var(--color-gray-600); font-size: 14px;
  display: flex; flex-direction: column; gap: 6px; align-items: center;
}
.state-box--err { color: var(--color-danger); }
.totals-line { font-size: 13px; font-weight: 600; color: var(--color-primary); margin: 12px 0 0; font-variant-numeric: tabular-nums; }
.print-sheet { display: none; }
.print-sheet h1 { font-size: 18px; margin: 0 0 4px; }
.print-sheet p { font-size: 12px; color: #555; margin: 0 0 12px; }
.print-sheet table { width: 100%; border-collapse: collapse; font-size: 12px; }
.print-sheet th, .print-sheet td { border: 1px solid #999; padding: 4px 8px; text-align: left; }
.print-foot { margin-top: 12px; font-weight: 600; }
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

<style>
@media print {
  body.printing .layout { display: none !important; }
  body.printing .print-sheet { display: block !important; }
}
</style>
