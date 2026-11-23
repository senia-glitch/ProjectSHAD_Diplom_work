<template>
  <div ref="root" class="picker">
    <button type="button" class="picker-btn" @click="open = !open">
      <span class="picker-ico" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="5.5" width="16" height="15" rx="2"/><path d="M4 10.5h16M8.5 3.5v4M15.5 3.5v4"/></svg>
      </span>
      <span>{{ label }}</span>
    </button>
    <div v-if="open" class="picker-pop">
      <div class="year-row">
        <button type="button" class="nav-arrow" @click="year -= 1" aria-label="Предыдущий год">‹</button>
        <span class="cal-title">{{ year }}</span>
        <button type="button" class="nav-arrow" @click="year += 1" aria-label="Следующий год">›</button>
      </div>
      <div class="month-grid">
        <button
          v-for="(m, i) in MONTHS" :key="m" type="button"
          :class="['month-cell', { 'month--sel': isSel(i), 'month--cur': isCur(i) }]"
          @click="pick(i)"
        >{{ m }}</button>
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

const MONTHS = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
const MONTHS_FULL = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

const open = ref(false)
const root = ref(null)
const now = new Date()
const year = ref(props.modelValue ? Number(props.modelValue.split('-')[0]) : now.getFullYear())
const curKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

const label = computed(() => {
  if (!props.modelValue) return 'Выбрать месяц'
  const [y, m] = props.modelValue.split('-').map(Number)
  return `${MONTHS_FULL[m - 1]} ${y}`
})

function isSel(i) {
  return props.modelValue === `${year.value}-${String(i + 1).padStart(2, '0')}`
}

function isCur(i) {
  return `${year.value}-${String(i + 1).padStart(2, '0')}` === curKey
}

function pick(i) {
  emit('update', `${year.value}-${String(i + 1).padStart(2, '0')}`)
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
.picker-btn:focus-visible { outline: none; border-color: var(--color-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent); }
.picker-ico { display: inline-flex; width: 16px; height: 16px; color: var(--color-gray-500); }
.picker-ico svg { width: 100%; height: 100%; }
.picker-pop {
  position: absolute; top: calc(100% + 8px); left: 0; z-index: 120;
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 12px; box-shadow: var(--shadow-md); padding: 12px;
  animation: pop-in 150ms ease-out; min-width: 232px;
}
.year-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.cal-title { font-size: 13px; font-weight: 600; color: var(--color-gray-800); }
.nav-arrow {
  border: none; background: none; cursor: pointer; font-size: 18px; line-height: 1;
  color: var(--color-gray-600); padding: 4px 10px; border-radius: 6px;
  transition: background 120ms ease-out;
}
.nav-arrow:hover { background: var(--color-gray-100); }
.month-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }
.month-cell {
  border: none; background: none; cursor: pointer; padding: 8px 4px;
  font-size: 12px; color: var(--color-gray-800); border-radius: 8px;
  transition: background 120ms ease-out;
}
.month-cell:hover { background: var(--color-gray-100); }
.month-cell.month--cur { box-shadow: inset 0 0 0 1.5px var(--color-accent); }
.month-cell.month--sel { background: var(--color-accent); color: var(--on-accent); font-weight: 600; }
.month-cell.month--sel.month--cur { box-shadow: inset 0 0 0 1.5px var(--color-white); }
@keyframes pop-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to { opacity: 1; transform: none; }
}
</style>
