<template>
  <div ref="root" class="picker">
    <button type="button" class="picker-btn" @click="toggle">
      <span class="picker-ico" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="5.5" width="16" height="15" rx="2"/><path d="M4 10.5h16M8.5 3.5v4M15.5 3.5v4"/></svg>
      </span>
      <span>{{ label }}</span>
    </button>
    <div v-if="open" class="picker-pop">
      <div class="cal-nav">
        <button type="button" class="nav-arrow" @click="shiftMonth(-1)" aria-label="Предыдущий месяц">‹</button>
        <span class="cal-title">{{ viewTitle }}</span>
        <button type="button" class="nav-arrow" @click="shiftMonth(1)" aria-label="Следующий месяц">›</button>
      </div>
      <div class="cal-dow"><span v-for="d in DOW" :key="d">{{ d }}</span></div>
      <div class="cal-grid">
        <div
          v-for="d in days" :key="d.key"
          :class="['day', `day--${d.kind}`, { 'day--sel': d.iso === modelValue, 'day--today': d.iso === todayStr }]"
          @click="pick(d.iso)"
        >{{ d.num }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update'])

const DOW = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

const open = ref(false)
const root = ref(null)
const todayStr = toISODate(new Date())
const view = ref((props.modelValue || todayStr).slice(0, 7))

function toISODate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function toggle() {
  if (!open.value && props.modelValue) view.value = props.modelValue.slice(0, 7)
  open.value = !open.value
}

function shiftMonth(n) {
  const [y, m] = view.value.split('-').map(Number)
  const d = new Date(y, m - 1 + n, 1)
  view.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const viewTitle = computed(() => {
  const [y, m] = view.value.split('-').map(Number)
  return `${MONTHS[m - 1]} ${y}`
})

// Сетка 6×7: захватываем хвосты соседних месяцев для ровного календаря.
const days = computed(() => {
  const [y, m] = view.value.split('-').map(Number)
  const first = new Date(y, m - 1, 1)
  const lead = (first.getDay() + 6) % 7
  const start = new Date(y, m - 1, 1 - lead)
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
    const iso = toISODate(d)
    return {
      key: iso,
      iso,
      num: d.getDate(),
      kind: d.getMonth() + 1 === m ? 'cur' : 'out',
    }
  })
})

const label = computed(() => {
  if (!props.modelValue) return 'Выбрать дату'
  const [y, m, d] = props.modelValue.split('-').map(Number)
  return `${d} ${MONTHS_SHORT[m - 1]} ${y}`
})

function pick(iso) {
  emit('update', iso)
  open.value = false
}

function onPointerDown(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}

function onKey(e) {
  if (e.key === 'Escape') open.value = false
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
.picker { position: relative; }
.picker-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 7px 12px; border: 1px solid var(--color-gray-300); border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--color-gray-800);
  background: var(--color-white); cursor: pointer; white-space: nowrap;
  transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}
.picker-btn:hover { border-color: var(--color-accent); }
.picker-btn:focus-visible { outline: none; border-color: var(--color-accent); box-shadow: 0 0 0 3px rgba(58, 122, 189, 0.18); }
.picker-ico { display: inline-flex; width: 16px; height: 16px; color: var(--color-gray-500); }
.picker-ico svg { width: 100%; height: 100%; }
.picker-pop {
  position: absolute; top: calc(100% + 8px); left: 0; z-index: 120;
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 12px; box-shadow: var(--shadow-md); padding: 12px;
  animation: pop-in 150ms ease-out;
}
.cal-nav { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.cal-title { font-size: 13px; font-weight: 600; color: var(--color-gray-800); }
.nav-arrow {
  border: none; background: none; cursor: pointer; font-size: 18px; line-height: 1;
  color: var(--color-gray-600); padding: 4px 10px; border-radius: 6px;
  transition: background 120ms ease-out;
}
.nav-arrow:hover { background: var(--color-gray-100); }
.cal-dow, .cal-grid { display: grid; grid-template-columns: repeat(7, 30px); gap: 2px; }
.cal-dow { margin-bottom: 4px; }
.cal-dow span { font-size: 10px; font-weight: 600; color: var(--color-gray-500); text-align: center; }
.day {
  height: 30px; display: flex; align-items: center; justify-content: center;
  font-size: 12px; color: var(--color-gray-800); border-radius: 8px; cursor: pointer;
  transition: background 120ms ease-out;
}
.day:hover { background: var(--color-gray-100); }
.day--out { color: var(--color-gray-400); }
.day--today { box-shadow: inset 0 0 0 1.5px var(--color-accent); }
.day--sel { background: var(--color-accent); color: var(--color-white); font-weight: 600; }
.day--sel.day--today { box-shadow: inset 0 0 0 1.5px var(--color-white); }
@keyframes pop-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to { opacity: 1; transform: none; }
}
</style>
