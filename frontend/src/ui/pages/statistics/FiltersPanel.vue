<template>
  <aside class="filters" :style="top != null ? { top: `${top}px` } : null">
    <h2 class="filters-title">Фильтры</h2>

    <section class="fgroup">
      <span class="fcap">Общее</span>
      <span class="fhint">Год и ученики влияют на всю страницу</span>
      <label class="fl">
        <span class="fl-label">Год</span>
        <select :value="filters.year" @change="setFilters({ year: Number($event.target.value) })">
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
      </label>
      <div ref="studentsWrap" class="students-wrap">
        <button type="button" class="students-btn" @click="pickerOpen = !pickerOpen">
          <span class="students-ico" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="3.5"/><path d="M5 19.5c1.5-3.5 4-5 7-5s5.5 1.5 7 5"/></svg>
          </span>
          {{ pickerLabel }}
        </button>
        <StudentPicker
          v-if="pickerOpen" :students="students" :selected="filters.studentIds"
          @toggle="toggleStudent($event)"
          @all="selectAllStudents(); pickerOpen = false"
        />
      </div>
      <button type="button" class="btn btn--gry btn--sm" @click="resetFilters()">Сбросить</button>
    </section>

    <template v-if="tab === 'dynamics'">
      <section class="fgroup">
        <span class="fcap">Таблица</span>
        <div class="seg" role="tablist" aria-label="Режим таблицы">
          <button
            v-for="m in dynModes" :key="m.value" type="button"
            :class="filters.dynMode === m.value ? 'seg-on' : ''"
            @click="setFilters({ dynMode: m.value })"
          >{{ m.label }}</button>
        </div>
        <label v-if="filters.dynMode === 'year'" class="fl">
          <span class="fl-label">Метрика таблицы</span>
          <select :value="filters.dynMetric" @change="setFilters({ dynMetric: $event.target.value })">
            <option v-for="m in dynMetrics" :key="m.value" :value="m.value" :disabled="m.disabled">{{ m.label }}</option>
          </select>
        </label>
      </section>

      <section class="fgroup">
        <span class="fcap">В отчёт</span>
        <label v-for="opt in includeOpts" :key="opt.key" class="check">
          <input
            type="checkbox" :checked="reportInclude[opt.key]"
            @change="setReportInclude({ [opt.key]: $event.target.checked })"
          /> {{ opt.label }}
        </label>
        <label class="check">
          <input type="checkbox" :checked="reportShowLinks" @change="setReportShowLinks($event.target.checked)" />
          Показывать ссылки на уроки
        </label>
      </section>
    </template>

    <template v-if="tab === 'payments'">
      <section class="fgroup">
        <span class="fcap">Период оплат</span>
        <label class="fl">
          <span class="fl-label">С</span>
          <input type="date" :value="paymentsDateFrom" @change="setPaymentsDateFrom($event.target.value)" />
        </label>
        <label class="fl">
          <span class="fl-label">По</span>
          <input type="date" :value="paymentsDateTo" @change="setPaymentsDateTo($event.target.value)" />
        </label>
      </section>

      <section class="fgroup">
        <span class="fcap">Ученик</span>
        <select :value="paymentsStudentId" @change="setPaymentsStudentId($event.target.value)">
          <option value="">Все ученики</option>
          <option v-for="s in students" :key="s.student_id" :value="String(s.student_id)">{{ s.full_name }}</option>
        </select>
      </section>

      <section class="fgroup">
        <span class="fcap">Статус оплаты</span>
        <div class="seg" role="tablist" aria-label="Статус оплаты">
          <button
            v-for="opt in paidOptions" :key="opt.value" type="button"
            :class="paymentsPaidFilter === opt.value ? 'seg-on' : ''"
            @click="setPaymentsPaidFilter(opt.value)"
          >{{ opt.label }}</button>
        </div>
      </section>
    </template>

    <template v-else>
      <section class="fgroup">
        <span class="fcap">Период</span>
        <PeriodControls :filters="filters" @update="setFilters($event)" bare />
      </section>

      <template v-if="tab === 'lessons'">
        <section class="fgroup">
          <span class="fcap">Статусы</span>
          <label v-for="s in statusOptions" :key="s.value" class="check">
            <input
              type="checkbox" :checked="lessonsStatuses.includes(s.value)"
              @change="toggleLessonsStatus(s.value)"
            /> {{ s.label }}
          </label>
        </section>

        <section class="fgroup">
          <span class="fcap">Тип</span>
          <div class="seg" role="tablist" aria-label="Тип уроков">
            <button
              v-for="t in typeOptions" :key="t.value" type="button"
              :class="lessonsType === t.value ? 'seg-on' : ''"
              @click="setLessonsType(t.value)"
            >{{ t.label }}</button>
          </div>
        </section>

        <section class="fgroup">
          <span class="fcap">Выгрузка</span>
          <div class="export-row">
            <button type="button" class="btn btn--pri btn--sm" @click="requestLessonsExport('csv')">CSV</button>
            <button type="button" class="btn btn--gry btn--sm" @click="requestLessonsExport('print')">Печать</button>
          </div>
        </section>
      </template>
    </template>
  </aside>
</template>

<script setup>
// Правый сайдбар страницы: всё управление — только здесь.
// Состав зависит от открытого блока: Динамика — таблица/метрика/«в отчёт»,
// Уроки — период/статусы/тип/выгрузка, Ученики — период.
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { DYN_METRICS, DYN_MODES, LESSON_STATUS_OPTIONS, LESSON_TYPE_OPTIONS } from '../../../logic/utils/index.js'
import { useStatisticsPage } from './useStatisticsPage.js'
import { useStatisticsStore } from '../../../logic/store/index.js'
import { usePaymentsPage } from '../payments/usePaymentsPage.js'
import StudentPicker from './StudentPicker.vue'
import PeriodControls from './PeriodControls.vue'

const props = defineProps({
  years: { type: Array, default: () => [] },
  students: { type: Array, default: () => [] },
  tab: { type: String, default: 'dynamics' },
  top: { type: Number, default: null },
})

const {
  filters, setFilters, resetFilters, toggleStudent, selectAllStudents,
} = useStatisticsPage()

const paymentsPage = usePaymentsPage()
const paymentsDateFrom = computed(() => paymentsPage.dateFrom.value)
const paymentsDateTo = computed(() => paymentsPage.dateTo.value)
const paymentsStudentId = computed(() => paymentsPage.studentId.value)
const paymentsPaidFilter = computed(() => paymentsPage.paidFilter.value)
const setPaymentsDateFrom = (v) => paymentsPage.dateFrom.value = v
const setPaymentsDateTo = (v) => paymentsPage.dateTo.value = v
const setPaymentsStudentId = (v) => paymentsPage.studentId.value = v
const setPaymentsPaidFilter = (v) => paymentsPage.paidFilter.value = v

const paidOptions = [
  { value: 'all', label: 'Все' },
  { value: 'paid', label: 'Оплаченные' },
  { value: 'unpaid', label: 'Неоплаченные' },
]
const statsStore = useStatisticsStore()
const reportInclude = computed(() => statsStore.reportInclude)
const reportShowLinks = computed(() => statsStore.reportShowLinks)
const lessonsStatuses = computed(() => statsStore.lessonsStatuses)
const lessonsType = computed(() => statsStore.lessonsType)
const setReportInclude = (p) => statsStore.setReportInclude(p)
const setReportShowLinks = (v) => statsStore.setReportShowLinks(v)
const toggleLessonsStatus = (v) => statsStore.toggleLessonsStatus(v)
const setLessonsType = (v) => statsStore.setLessonsType(v)
const requestLessonsExport = (kind) => statsStore.requestLessonsExport(kind)

const pickerOpen = ref(false)
const studentsWrap = ref(null)

const pickerLabel = computed(() => {
  if (!filters.studentIds.length) return 'Ученики'
  if (filters.studentIds.length === 1) {
    const found = (props.students || []).find((s) => s.student_id === filters.studentIds[0])
    return `Ученик: ${found ? found.full_name : `#${filters.studentIds[0]}`}`
  }
  return `Ученики: ${filters.studentIds.length}`
})

const dynModes = DYN_MODES
const dynMetrics = DYN_METRICS
const statusOptions = LESSON_STATUS_OPTIONS
const typeOptions = LESSON_TYPE_OPTIONS
const includeOpts = [
  { key: 'conducted', label: 'Проведённые' },
  { key: 'planned', label: 'Запланированные' },
  { key: 'cancelled', label: 'Отмены' },
  { key: 'paid', label: 'Оплаченные' },
  { key: 'unpaid', label: 'Неоплаченные' },
]

function onPointerDown(e) {
  if (pickerOpen.value && studentsWrap.value && !studentsWrap.value.contains(e.target)) {
    pickerOpen.value = false
  }
}

function onKey(e) {
  if (e.key === 'Escape' && pickerOpen.value) pickerOpen.value = false
}

onMounted(() => {
  document.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('pointerdown', onPointerDown)
  window.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.filters {
  position: sticky; align-self: start;
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 14px; box-shadow: var(--shadow-sm); padding: 16px 18px;
  display: flex; flex-direction: column; gap: 16px;
  max-height: calc(100vh - 100px); overflow-y: auto;
}
.filters-title { margin: 0; font-size: 15px; font-weight: 700; color: var(--color-primary); }
.fgroup { display: flex; flex-direction: column; gap: 10px; }
.fgroup + .fgroup { border-top: 1px solid var(--color-gray-100); padding-top: 14px; }
.fcap {
  font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--color-gray-500);
}
.fhint { font-size: 11px; color: var(--color-gray-500); margin-top: -6px; }
.fl { display: flex; flex-direction: column; gap: 4px; }
.fl-label { font-size: 12px; color: var(--color-gray-600); }
.fl select {
  padding: 7px 10px; border: 1px solid var(--color-gray-300);
  border-radius: 8px; font-size: 13px; font-weight: 500; background: var(--color-white);
  color: var(--color-gray-800); cursor: pointer; width: 100%; box-sizing: border-box;
}
.fl select:hover { border-color: var(--color-accent); }
.fl select:focus-visible { outline: none; border-color: var(--color-accent); box-shadow: 0 0 0 3px rgba(58, 122, 189, 0.18); }
.seg { display: flex; background: var(--color-gray-100); border-radius: 9px; padding: 3px; gap: 2px; }
.seg button {
  flex: 1; border: none; background: none; cursor: pointer; font-size: 12px; font-weight: 500;
  color: var(--color-gray-600); padding: 6px 12px; border-radius: 7px; white-space: nowrap;
}
.seg button:hover { color: var(--color-gray-800); }
.seg button.seg-on { background: var(--color-white); color: var(--color-gray-800); box-shadow: var(--shadow-sm); }
.students-wrap { position: relative; }
.students-btn {
  display: inline-flex; align-items: center; gap: 8px; width: 100%; box-sizing: border-box;
  padding: 7px 12px; border: 1px solid var(--color-gray-300); border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--color-gray-800);
  background: var(--color-white); cursor: pointer; white-space: nowrap;
}
.students-btn:hover { border-color: var(--color-accent); }
.students-btn:focus-visible { outline: none; border-color: var(--color-accent); box-shadow: 0 0 0 3px rgba(58, 122, 189, 0.18); }
.students-ico { display: inline-flex; width: 16px; height: 16px; color: var(--color-gray-500); flex-shrink: 0; }
.students-ico svg { width: 100%; height: 100%; }
.check { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--color-gray-700); cursor: pointer; }
.check input { width: auto; }
.export-row { display: flex; gap: 8px; }
</style>
