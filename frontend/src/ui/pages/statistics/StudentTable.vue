<template>
  <div class="table-panel">
    <div class="table-head">
      <h3 class="table-title">По ученикам</h3>
      <div class="table-tools">
        <input
          v-if="rows.length > 3"
          v-model="query" type="search" placeholder="Найти ученика…" class="table-search"
        />
        <button type="button" class="btn btn--sm btn--pri" @click="exportCsv">CSV</button>
      </div>
    </div>
    <div class="filter-groups">
      <button
        type="button" class="btn btn--sm"
        :class="actFilter === 'all' && payFilter === 'all' ? 'btn--pri' : 'btn--gry'"
        @click="resetView"
      >Все</button>
      <span class="filter-cat">
        <span class="filter-cap">Активность</span>
        <button
          type="button" class="btn btn--sm" :class="actFilter === 'active' ? 'btn--pri' : 'btn--gry'"
          @click="toggleAct('active')"
        >Активные</button>
        <button
          type="button" class="btn btn--sm" :class="actFilter === 'inactive' ? 'btn--pri' : 'btn--gry'"
          @click="toggleAct('inactive')"
        >Неактивные</button>
      </span>
      <span class="filter-cat">
        <span class="filter-cap">Оплата</span>
        <button
          type="button" class="btn btn--sm" :class="payFilter === 'debt' ? 'btn--pri' : 'btn--gry'"
          @click="togglePay('debt')"
        >С долгом</button>
        <button
          type="button" class="btn btn--sm" :class="payFilter === 'nodebt' ? 'btn--pri' : 'btn--gry'"
          @click="togglePay('nodebt')"
        >Без долга</button>
      </span>
    </div>
    <div v-if="!visibleRows.length" class="table-empty">
      {{ rows.length ? 'В этом подрежиме пусто' : 'Нет данных за период' }}
    </div>
    <div v-else class="table-scroll">
      <table class="stable">
        <thead>
          <tr>
            <th
              v-for="c in columns" :key="c.key"
              :class="[{ num: c.num, sorted: sortKey === c.key }]"
              @click="c.sortable && toggleSort(c.key)"
            >{{ c.label }}<span v-if="sortKey === c.key" class="sort-arrow">{{ sortDir === 1 ? ' ▲' : ' ▼' }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in visibleRows" :key="r.student_id" class="clickable" @click="emit('select', r)">
            <td>{{ r.student_name }}</td>
            <td class="num">{{ r.lessons }}</td>
            <td class="num">{{ formatHours(r.billed_hours) }}</td>
            <td class="num">
              {{ formatMoney(r.revenue) }}<span v-if="r.estimated > 0" title="Часть сумм оценочная"> ≈</span>
            </td>
            <td class="num">{{ r.cancelled }} / {{ r.no_show }}</td>
            <td class="num">{{ formatMoney(r.forecast_revenue) }}</td>
            <td class="num">{{ r._avg ? formatMoney(r._avg) : '—' }}</td>
            <td>{{ statusText(r) }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td>Итого</td>
            <td class="num">{{ totals.lessons }}</td>
            <td class="num">{{ formatHours(totals.hours) }}</td>
            <td class="num">{{ formatMoney(totals.revenue) }}</td>
            <td class="num">{{ totals.cancelled }} / {{ totals.noShow }}</td>
            <td class="num">{{ formatMoney(totals.forecast) }}</td>
            <td class="num">{{ totals.lessons ? formatMoney(Math.round(totals.revenue / totals.lessons)) : '—' }}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatMoney, formatHours } from '../../../logic/utils/index.js'
import { studentsTableToCsv, reportFileName, downloadText } from './studentCsv.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  // Долг по ученикам: { student_id: сумма неоплаченных проведённых }.
  debtById: { type: Object, default: () => ({}) },
  period: { type: String, default: '' },
})
const emit = defineEmits(['select'])

const actFilter = ref('all')
const payFilter = ref('all')
const query = ref('')
const sortKey = ref('revenue')
const sortDir = ref(-1)

function toggleAct(v) {
  actFilter.value = actFilter.value === v ? 'all' : v
}

function togglePay(v) {
  payFilter.value = payFilter.value === v ? 'all' : v
}

function resetView() {
  actFilter.value = 'all'
  payFilter.value = 'all'
}

function debtOf(id) {
  return (props.debtById || {})[id] || 0
}
const columns = [
  { key: 'student_name', label: 'Ученик', num: false, sortable: true },
  { key: 'lessons', label: 'Уроки', num: true, sortable: true },
  { key: 'billed_hours', label: 'Часы', num: true, sortable: true },
  { key: 'revenue', label: 'Выручка', num: true, sortable: true },
  { key: 'missed', label: 'Отм. / неявки', num: true, sortable: true },
  { key: 'forecast_revenue', label: 'Прогноз', num: true, sortable: true },
  { key: '_avg', label: 'Средний чек', num: true, sortable: true },
  { key: 'status', label: 'Статус', num: false, sortable: false },
]

// Активность — только из настроек ученика (ACTIVE/INACTIVE).
// Не INACTIVE считается активным — так же считает бэк по умолчанию.
const isInactive = (r) => r.status === 'INACTIVE'

const enriched = computed(() => props.rows.map((r) => {
  return { ...r, missed: r.cancelled + r.no_show, _avg: r.lessons ? Math.round(r.revenue / r.lessons) : 0 }
}))

const visibleRows = computed(() => {
  const q = query.value.trim().toLowerCase()
  let list = enriched.value
  if (actFilter.value === 'active') list = list.filter((r) => !isInactive(r))
  if (actFilter.value === 'inactive') list = list.filter((r) => isInactive(r))
  if (payFilter.value === 'debt') list = list.filter((r) => debtOf(r.student_id) > 0)
  if (payFilter.value === 'nodebt') list = list.filter((r) => debtOf(r.student_id) === 0)
  if (q) list = list.filter((r) => r.student_name.toLowerCase().includes(q))
  const dir = sortDir.value
  return [...list].sort((a, b) => {
    const av = a[sortKey.value]
    const bv = b[sortKey.value]
    if (typeof av === 'string') return av.localeCompare(bv, 'ru') * dir
    return ((av ?? 0) - (bv ?? 0)) * dir
  })
})

const totals = computed(() => visibleRows.value.reduce((s, r) => ({
  lessons: s.lessons + r.lessons,
  hours: Math.round((s.hours + r.billed_hours) * 100) / 100,
  revenue: s.revenue + r.revenue,
  cancelled: s.cancelled + r.cancelled,
  noShow: s.noShow + r.no_show,
  forecast: s.forecast + r.forecast_revenue,
}), { lessons: 0, hours: 0, revenue: 0, cancelled: 0, noShow: 0, forecast: 0 }))

function toggleSort(key) {
  if (sortKey.value === key) sortDir.value = -sortDir.value
  else {
    sortKey.value = key
    sortDir.value = key === 'student_name' ? 1 : -1
  }
}

function statusText(r) {
  return isInactive(r) ? 'Неактивен' : 'Активен'
}

function exportCsv() {
  const rows = visibleRows.value.map((r) => ({ ...r, statusText: statusText(r) }))
  downloadText(reportFileName('students_table', props.period), studentsTableToCsv(rows, props.debtById))
}

</script>

<style scoped>
.table-panel {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg); padding: 16px 20px;
}
.table-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.table-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--color-primary); }
.table-search {
  padding: 6px 10px; border: 1px solid var(--color-gray-300); border-radius: 6px;
  font-size: 13px; background: var(--color-white); width: 180px; box-sizing: border-box;
}
.table-search:focus { outline: none; border-color: var(--color-accent); }
.table-tools { display: flex; align-items: center; gap: 8px; }
.filter-groups { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; margin-bottom: 12px; }
.filter-cat { display: inline-flex; align-items: center; gap: 6px; }
.filter-cap { font-size: 11px; font-weight: 600; color: var(--color-gray-500); }
.table-empty { padding: 16px; text-align: center; color: var(--color-gray-500); font-size: 13px; }
.table-scroll { max-height: 480px; overflow-y: auto; }
.stable { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; border: 1px solid var(--color-gray-200); border-radius: 8px; }
.stable thead th {
  position: sticky; top: 0; z-index: 2; background: var(--color-white);
  padding: 8px 10px; border-bottom: 2px solid var(--color-gray-200);
  text-align: left; color: var(--color-gray-600); font-weight: 600; font-size: 12px;
  cursor: pointer; user-select: none; white-space: nowrap;
}
.stable thead th.sorted { color: var(--color-accent-dark); }
.stable tbody td { padding: 8px 10px; border-bottom: 1px solid var(--color-gray-100); text-align: left; }
.stable th + th, .stable td + td { border-left: 1px solid var(--color-gray-100); }
.stable .num { text-align: right; font-variant-numeric: tabular-nums; }
.stable tbody tr.clickable { cursor: pointer; }
.stable tbody tr.clickable:hover td { background: var(--color-gray-50); }
.stable tfoot td {
  position: sticky; bottom: 0; z-index: 2; background: var(--color-white);
  padding: 8px 10px; border-top: 2px solid var(--color-gray-200);
  font-weight: 600; color: var(--color-gray-800); font-variant-numeric: tabular-nums;
}
.stable tbody tr:last-child td { border-bottom: none; }
.stable thead th:first-child { border-top-left-radius: 7px; }
.stable thead th:last-child { border-top-right-radius: 7px; }
.stable tfoot td:first-child { border-bottom-left-radius: 7px; }
.stable tfoot td:last-child { border-bottom-right-radius: 7px; }
.sort-arrow { font-size: 10px; }
</style>
