<template>
  <div class="donut">
    <div class="donut-chart">
      <svg :width="size" :height="size" viewBox="0 0 120 120" role="img" :aria-label="title">
        <circle cx="60" cy="60" :r="R" fill="none" :stroke-width="W" class="donut-track" />
        <circle
          v-for="(s, i) in laidOut" :key="s.key"
          cx="60" cy="60" :r="R" fill="none" :stroke="s.color" :stroke-width="W"
          :stroke-dasharray="`${s.len} ${C - s.len}`"
          :stroke-dashoffset="-s.off"
          class="donut-seg"
          :class="{ 'donut-seg--dim': highlighted && highlighted !== s.key }"
          @click="toggle(s.key)"
        />
      </svg>
      <div v-if="centerText" class="donut-center">{{ centerText }}</div>
    </div>
    <div class="donut-legend">
      <div class="legend-title">{{ title }}</div>
      <button
        v-for="s in laidOut" :key="s.key" type="button"
        class="legend-row"
        :class="{ 'legend-row--hi': highlighted === s.key }"
        @click="toggle(s.key)"
      >
        <i :style="{ background: s.color }"></i>
        <span class="legend-label">{{ s.label }}</span>
        <span class="legend-val">{{ s.text }}</span>
      </button>
      <div
        v-for="extra in extras" :key="extra.key"
        class="legend-row legend-row--static"
      >
        <i :style="{ background: extra.color }"></i>
        <span class="legend-label">{{ extra.label }}</span>
        <span class="legend-val">{{ extra.text }}</span>
      </div>
      <p v-if="caption" class="legend-cap">{{ caption }}</p>
    </div>
  </div>
</template>

<script setup>
// Кольцевая диаграмма: на диаграмме надписей нет, легенда под ней.
// Клик по сегменту подсвечивает легенду (и наоборот).
// Тонкие дольки — минимальный видимый угол, масштаб условный.
import { ref, computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  segments: { type: Array, default: () => [] },
  extras: { type: Array, default: () => [] },
  centerText: { type: String, default: '' },
  caption: { type: String, default: '' },
  size: { type: Number, default: 150 },
})
const emit = defineEmits(['select'])

const R = 48
const W = 22
const C = 2 * Math.PI * R
// Минимальный видимый угол дольки: диаграмма для восприятия,
// масштаб условный (подпись под легендой).
const MIN_FRAC = 12 / 360

const highlighted = ref('')

function toggle(key) {
  highlighted.value = highlighted.value === key ? '' : key
  emit('select', highlighted.value)
}

const laidOut = computed(() => {
  const total = props.segments.reduce((s, x) => s + (x.value || 0), 0)
  if (total <= 0) return props.segments.map((x) => ({ ...x, len: 0, off: 0 }))
  let raws = props.segments.map((x) => (x.value || 0) / total)
  raws = raws.map((f) => (f > 0 && f < MIN_FRAC ? MIN_FRAC : f))
  const sum = raws.reduce((s, f) => s + f, 0) || 1
  let acc = C * 0.25
  return props.segments.map((x, i) => {
    const len = (raws[i] / sum) * C
    const off = acc
    acc += len
    return { ...x, len: Math.max(0, len - 1.5), off }
  })
})
</script>

<style scoped>
.donut { display: flex; gap: 18px; align-items: center; flex-wrap: wrap; }
.donut-chart { position: relative; flex-shrink: 0; }
.donut-track { stroke: var(--color-gray-100); }
.donut-seg { cursor: pointer; transition: opacity 150ms; }
.donut-seg--dim { opacity: 0.25; }
.donut-center {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; color: var(--color-gray-800); pointer-events: none;
}
.donut-legend { display: flex; flex-direction: column; gap: 4px; min-width: 220px; flex: 1; }
.legend-title { font-size: 13px; font-weight: 600; color: var(--color-gray-800); margin-bottom: 4px; }
.legend-row {
  display: flex; align-items: center; gap: 8px; width: 100%;
  background: none; border: 1px solid transparent; border-radius: 8px;
  padding: 4px 8px; font-size: 13px; color: var(--color-gray-700); cursor: pointer;
  text-align: left;
}
.legend-row:hover { background: var(--color-gray-50); }
.legend-row--hi { border-color: var(--color-accent); background: var(--color-accent-50); }
.legend-row--static { cursor: default; }
.legend-row--static:hover { background: none; }
.legend-row i { width: 12px; height: 12px; border-radius: 4px; flex-shrink: 0; }
.legend-label { flex: 1; }
.legend-val { font-weight: 600; color: var(--color-gray-800); white-space: nowrap; }
.legend-cap { margin: 4px 0 0; font-size: 11px; color: var(--color-gray-500); }
</style>
