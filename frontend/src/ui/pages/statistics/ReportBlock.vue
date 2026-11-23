<template>
  <section class="report">
    <div class="report-head">
      <div>
        <h2 class="report-title">Информация-отчёт</h2>
        <p class="report-range">{{ rangeLabel }}</p>
      </div>
    </div>

    <div class="fin-card">
      <div class="fin-main">
        <span class="fin-cap">Выручка (проведённые оплаченные)</span>
        <span class="fin-sum">{{ money(agg.finance.revenue) }}</span>
      </div>
      <div class="fin-grid">
        <div class="fin-cell">
          <span class="fin-cap">Средняя цена по выручке</span>
          <span class="fin-val">{{ money(agg.finance.avgPaid) }}</span>
          <span class="fin-sub">по {{ plural(agg.finance.avgPaidCount, ['линия', 'линии', 'линий']) }}</span>
        </div>
        <div class="fin-cell">
          <span class="fin-cap">Средняя цена запланированных</span>
          <span class="fin-val">{{ money(agg.finance.avgPlanned) }}</span>
          <span class="fin-sub">потенциал · {{ plural(agg.finance.avgPlannedCount, ['урок', 'урока', 'уроков']) }}</span>
        </div>
        <div class="fin-cell">
          <span class="fin-cap">Средняя цена любых</span>
          <span class="fin-val">{{ money(agg.finance.avgAny) }}</span>
          <span class="fin-sub">{{ plural(agg.finance.avgAnyCount, ['урок', 'урока', 'уроков']) }} всего</span>
        </div>
        <div class="fin-cell">
          <span class="fin-cap">Средняя длительность</span>
          <span class="fin-val">{{ agg.finance.avgDurConducted }} мин</span>
          <span class="fin-sub">проведённые · план {{ agg.finance.avgDurPlanned }} · все {{ agg.finance.avgDurAny }}</span>
        </div>
      </div>
    </div>

    <div class="donut-grid">
      <div class="donut-card">
        <ReportDonut
          title="Уроки"
          :segments="lessonSegments"
          :extras="lessonExtras"
          :center-text="String(agg.lessonsDonut.conducted + agg.lessonsDonut.planned)"
        />
      </div>
      <div class="donut-card">
        <ReportDonut
          title="Время"
          :segments="timeSegments"
          :center-text="`${trim1(agg.timeDonut.conductedH + agg.timeDonut.plannedH)} ч`"
          caption="Масштаб условный: тонкие дольки показаны минимальным углом."
        />
      </div>
    </div>

    <div class="list-card">
      <div class="list-head">
        <h3 class="list-title">Уроки ({{ filteredRows.length }})</h3>
        <button type="button" class="btn btn--pri btn--sm" @click="downloadCsv">Скачать CSV отчёта</button>
      </div>
      <div v-if="!filteredRows.length" class="list-empty">Нет записей под выбранные флаги.</div>
      <div v-else class="list-scroll">
        <div v-for="r in filteredRows" :key="`${r.lesson_id}_${r.student_id}`" class="line">
          <div class="line-main">
            <span class="line-date">{{ fmtDate(r.date) }}</span>
            <span class="line-time">{{ r.start }}–{{ r.end }}</span>
            <span class="line-name">{{ r.name }}</span>
            <span class="line-min">{{ r.minutes }} мин</span>
            <span class="line-status">{{ statusLabel(r.status) }}</span>
            <span class="line-sum">{{ money(r.amount) }}</span>
            <span class="line-pay" :class="r.paid ? 'line-pay--yes' : ''">{{ r.paid ? 'оплачен' : 'не оплачен' }}</span>
            <button
              v-if="showLinks && r.links.length" type="button"
              class="btn btn--gry btn--sm" @click="toggleLinks(r)"
            >{{ openLinks.has(linkKey(r)) ? 'Скрыть' : 'Ссылки' }}</button>
          </div>
          <div v-if="showLinks && openLinks.has(linkKey(r))" class="line-links">
            <a v-for="(x, i) in r.links" :key="i" :href="safeUrl(x.url)" target="_blank" rel="noopener">{{ x.alias || x.url }}</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
// Блок «Информация-отчёт»: финансы, два кольца, список, CSV.
// «Что включаем» и показ ссылок живут в сторе: контролы — в сайдбаре.
// Выбор влияет на список и CSV; диаграммы — весь скоуп периода.
import { ref, computed } from 'vue'
import ReportDonut from './ReportDonut.vue'
import { useStatisticsStore } from '../../../logic/store/index.js'
import { filterLines, reportToCsv } from '../../../logic/utils/index.js'
import { formatMoney, safeUrl } from '../../../logic/utils/index.js'
import { downloadText } from './studentCsv.js'

const props = defineProps({
  title: { type: String, default: 'Отчёт' },
  rangeLabel: { type: String, default: '' },
  agg: { type: Object, default: null },
  rows: { type: Array, default: () => [] },
  fileSuffix: { type: String, default: 'report' },
})

const statsStore = useStatisticsStore()
const include = computed(() => statsStore.reportInclude)
const showLinks = computed(() => statsStore.reportShowLinks)
const openLinks = ref(new Set())

const filteredRows = computed(() => filterLines(props.rows, include.value))

const STATUS_LABEL = { FINISHED: 'проведён', SCHEDULED: 'запланирован', ONGOING: 'идёт', CANCELLED: 'отменён', NO_SHOW: 'неявка' }

function statusLabel(s) {
  return STATUS_LABEL[s] || s || '—'
}

function money(v) {
  return formatMoney(v)
}

function trim1(v) {
  return String(Math.round((v || 0) * 10) / 10).replace('.', ',')
}

function plural(n, forms) {
  const v = Math.abs(n || 0) % 100
  const d = v % 10
  if (v > 10 && v < 20) return `${n} ${forms[2]}`
  if (d > 1 && d < 5) return `${n} ${forms[1]}`
  if (d === 1) return `${n} ${forms[0]}`
  return `${n} ${forms[2]}`
}

function fmtDate(iso) {
  return iso ? iso.split('-').reverse().join('.') : '—'
}

function linkKey(r) {
  return `${r.lesson_id}_${r.student_id}`
}

function toggleLinks(r) {
  const k = linkKey(r)
  const next = new Set(openLinks.value)
  if (next.has(k)) next.delete(k)
  else next.add(k)
  openLinks.value = next
}

const lessonSegments = computed(() => {
  const d = props.agg?.lessonsDonut || {}
  return [
    { key: 'conducted', label: `Завершённые (линии: опл. ${d.conductedPaid || 0} / неопл. ${d.conductedUnpaid || 0})`, value: d.conducted || 0, text: String(d.conducted || 0), color: '#3a7abd' },
    { key: 'planned', label: `Запланированные (линии: опл. ${d.plannedPaid || 0} / неопл. ${d.plannedUnpaid || 0})`, value: d.planned || 0, text: String(d.planned || 0), color: '#e67700' },
  ]
})

const lessonExtras = computed(() => {
  const d = props.agg?.lessonsDonut || {}
  // Отмены записей по инициаторам считает бэкенд (поле cancelled в записи).
  const byS = d.cancelledByStudent || 0
  const byT = d.cancelledByTutor || 0
  return [
    { key: 'cancelled', label: `Отмены записей (вне диаграммы): ученик ${byS} / репетитор ${byT}`, value: 0, text: String(d.cancelled || 0), color: '#c92a2a' },
  ]
})

const timeSegments = computed(() => {
  const t = props.agg?.timeDonut || {}
  return [
    { key: 'conducted', label: `Завершённые ${trim1(t.conductedH)} ч · опл. ${trim1(t.conductedPaidH)} / неопл. ${trim1(t.conductedUnpaidH)}`, value: t.conductedH || 0, text: `${trim1(t.conductedH)} ч`, color: '#3a7abd' },
    { key: 'planned', label: `Запланированные ${trim1(t.plannedH)} ч · опл. ${trim1(t.plannedPaidH)} / неопл. ${trim1(t.plannedUnpaidH)}`, value: t.plannedH || 0, text: `${trim1(t.plannedH)} ч`, color: '#e67700' },
    { key: 'free', label: 'Незанятое', value: t.freeH || 0, text: `${trim1(t.freeH)} ч`, color: '#dee2e6' },
  ]
})

function downloadCsv() {
  const csv = reportToCsv({
    title: props.title,
    rangeLabel: props.rangeLabel,
    agg: props.agg,
    rows: filteredRows.value,
    showLinks: showLinks.value,
  })
  const safe = props.fileSuffix.replace(/[^0-9A-Za-z_-]+/g, '_')
  downloadText(`statistika_otchet_${safe}.csv`, csv)
}
</script>

<style scoped>
.report { display: flex; flex-direction: column; gap: 16px; }
.report-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.report-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin: 0; }
.report-range { margin: 2px 0 0; font-size: 13px; color: var(--color-gray-600); }
.fin-card, .donut-card, .list-card {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 14px; box-shadow: var(--shadow-sm); padding: 16px 18px;
}
.fin-main { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.fin-cap { font-size: 12px; color: var(--color-gray-600); }
.fin-sum { font-size: 24px; font-weight: 700; color: var(--color-gray-800); }
.fin-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.fin-cell { display: flex; flex-direction: column; gap: 2px; }
.fin-val { font-size: 16px; font-weight: 600; color: var(--color-gray-800); }
.fin-sub { font-size: 11px; color: var(--color-gray-500); }
.donut-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.list-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.list-title { font-size: 14px; font-weight: 600; margin: 0; color: var(--color-gray-800); }
.list-empty { font-size: 13px; color: var(--color-gray-500); }
.list-scroll { display: flex; flex-direction: column; gap: 6px; max-height: 420px; overflow-y: auto; }
.line { border: 1px solid var(--color-gray-100); border-radius: 8px; padding: 8px 10px; }
.line-main { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px; }
.line-date { font-weight: 600; }
.line-time, .line-min, .line-status { color: var(--color-gray-600); }
.line-name { flex: 1; min-width: 120px; }
.line-sum { font-weight: 600; }
.line-pay { color: var(--color-danger); }
.line-pay--yes { color: var(--color-success); }
.line-links { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 6px; font-size: 12px; }
@media (max-width: 900px) {
  .fin-grid { grid-template-columns: 1fr 1fr; }
  .donut-grid { grid-template-columns: 1fr; }
}
</style>
