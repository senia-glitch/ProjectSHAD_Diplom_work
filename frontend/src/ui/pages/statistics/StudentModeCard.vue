<template>
  <div v-if="row" class="mode-card">
    <div class="mode-head">
      <div class="mode-avatar">{{ initial }}</div>
      <div class="mode-id">
        <h3 class="mode-name">{{ row.student_name }}</h3>
        <StudentStatusChip :status="row.status" />
      </div>
    </div>
    <div class="mode-grid">
      <div class="mode-stat"><span class="mode-v">{{ row.lessons }}</span><span class="mode-k">уроков</span></div>
      <div class="mode-stat"><span class="mode-v">{{ formatHours(row.billed_hours) }}</span><span class="mode-k">часы</span></div>
      <div class="mode-stat"><span class="mode-v">{{ formatMoney(row.revenue) }}</span><span class="mode-k">выручка</span></div>
      <div class="mode-stat"><span class="mode-v">{{ avgCheck }}</span><span class="mode-k">средний чек</span></div>
    </div>
    <div class="mode-spark-block">
      <div class="mode-spark-head">
        <span class="mode-spark-title">{{ sparkTitle }}</span>
        <span class="mode-legend"><i class="lg-fact"></i>факт<i class="lg-fore"></i>прогноз</span>
      </div>
      <VisXYContainer v-if="spark.length > 1" :data="spark" :margin="{ top: 4, left: 44, right: 4, bottom: 20 }" :yDomain="[0, sparkTop]" class="mode-spark">
        <VisArea :x="(d) => d.i" :y="(d) => d.v" :color="ACCENT" :opacity="0.2" />
        <VisLine :x="(d) => d.i" :y="(d) => d.v" :color="ACCENT" :lineWidth="2" />
        <VisLine :x="(d) => d.i" :y="(d) => d.f" :color="FORECAST" :lineWidth="2" :lineDashArray="[5, 4]" />
        <VisAxis type="y" :numTicks="3" :tickFormat="(v) => shortMoney(v)" :gridLine="false" :tickTextColor="GRAY_TEXT" :tickTextFontSize="10" :domainLine="false" />
        <VisAxis
          type="x" :tickValues="sparkTicks" :tickFormat="(i) => sparkLabels[i] || ''"
          :gridLine="false" :tickTextColor="GRAY_TEXT" :tickTextFontSize="10"
        />
      </VisXYContainer>
      <p v-else class="mode-spark-empty">Недостаточно данных для графика</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VisXYContainer, VisArea, VisLine, VisAxis } from '@unovis/vue'
import { formatMoney, formatHours, bucketLabel, alignSeries } from '../../../logic/utils/index.js'
import { cssVar } from './cssVars.js'
import StudentStatusChip from './StudentStatusChip.vue'

const props = defineProps({
  row: { type: Object, default: null },
  series: { type: Array, default: () => [] },
  // Полная сетка бакетов периода: график всегда покрывает весь диапазон
  // фильтров, пустые бакеты — нули (иначе «сен–окт при фильтре год»).
  buckets: { type: Array, default: () => [] },
  granularity: { type: String, default: 'month' },
})

const ACCENT = cssVar('--color-accent')
const FORECAST = cssVar('--chart-forecast', '#e67700')
const GRAY_TEXT = cssVar('--color-gray-500', '#adb5bd')
const initial = computed(() => (props.row?.student_name || '?').charAt(0).toUpperCase())
const avgCheck = computed(() => {
  if (!props.row?.lessons) return '—'
  return formatMoney(Math.round(props.row.revenue / props.row.lessons))
})
// Заголовок следует за шагом фильтров: ряд строится в гранулярности периода.
const sparkTitle = computed(() => {
  if (props.granularity === 'day') return 'Оплата занятий по дням'
  if (props.granularity === 'week') return 'Оплата занятий по неделям'
  return 'Оплата занятий по месяцам'
})

const spark = computed(() => {
  const cells = (props.series || []).filter((c) => props.row && c.student_id === props.row.student_id)
  const grid = props.buckets.length ? props.buckets : [...new Set(cells.map((c) => c.bucket))].sort()
  return alignSeries(grid, cells).map((c, i) => ({ i, v: c.revenue, f: c.forecast, bucket: c.bucket }))
})

const sparkLabels = computed(() => spark.value.map((p) => bucketLabel(p.bucket, props.granularity)))
const sparkTicks = computed(() => {
  const n = spark.value.length
  const step = Math.max(1, Math.ceil(n / 6))
  return Array.from({ length: n }, (_, i) => i).filter((i) => i % step === 0)
})

const sparkTop = computed(() => {
  const m = Math.max(1, ...spark.value.map((p) => Math.max(p.v, p.f)))
  if (!Number.isFinite(m) || m <= 0) return 1
  const exp = Math.floor(Math.log10(m))
  const f = m / 10 ** exp
  const nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10
  return nf * 10 ** exp
})

function shortMoney(v) {
  if (v >= 1000) return `${Math.round(v / 100) / 10}к`
  return String(Math.round(v))
}
</script>

<style scoped>
.mode-card {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg); padding: 18px 22px;
  display: flex; flex-direction: column; gap: 14px;
}
.mode-head { display: flex; align-items: center; gap: 14px; }
.mode-avatar {
  width: 48px; height: 48px; border-radius: var(--radius-full); background: var(--color-primary);
  display: flex; align-items: center; justify-content: center;
  color: var(--color-white); font-size: 20px; font-weight: 600; flex-shrink: 0;
}
.mode-id { display: flex; flex-direction: column; gap: 4px; }
.mode-name { margin: 0; font-size: 20px; font-weight: 600; color: var(--color-primary); }
.mode-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px; }
.mode-stat { display: flex; flex-direction: column; gap: 2px; }
.mode-stat .mode-v { font-size: 19px; font-weight: 600; color: var(--color-gray-800); font-variant-numeric: tabular-nums; }
.mode-stat .mode-k { font-size: 12px; color: var(--color-gray-600); }
.mode-spark { height: 84px; width: 100%; }
.mode-spark-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.mode-spark-title { font-size: 12px; font-weight: 600; color: var(--color-gray-600); }
.mode-legend { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: var(--color-gray-600); }
.mode-legend .lg-fact { width: 14px; height: 3px; background: var(--color-accent); border-radius: 2px; display: inline-block; }
.mode-legend .lg-fore { width: 14px; height: 0; border-top: 2px dashed var(--chart-forecast); display: inline-block; margin-left: 6px; }
.mode-spark-empty { font-size: 12px; color: var(--color-gray-500); margin: 0; }
</style>
