<template>
  <div class="month-grid">
    <div class="mg-head">
      <span v-for="day in WEEKDAY_ORDER" :key="day" class="mg-wd">{{ WEEKDAY_SHORT[day] }}</span>
    </div>
    <div class="mg-body">
      <div v-for="(week, wi) in weeks" :key="wi" class="mg-week">
        <button
          v-for="cell in week"
          :key="cell.iso"
          type="button"
          class="mg-cell"
          :aria-label="new Date(`${cell.iso}T00:00:00`).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })"
          :aria-pressed="cell.iso === selectedDay"
          :aria-current="cell.iso === todayIso ? 'date' : undefined"
          :class="{
            'mg-cell--out': !cell.inMonth,
            'mg-cell--today': cell.iso === todayIso,
            'mg-cell--sel': cell.iso === selectedDay,
          }"
          @click="emit('pick', cell.iso)"
        >
          <span class="mg-day">{{ cell.day }}</span>
          <span v-if="counts[cell.iso]" class="mg-count">{{ counts[cell.iso] }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { WEEKDAY_ORDER, WEEKDAY_SHORT } from '../../../logic/constants/index.js'

defineProps({
  weeks: { type: Array, default: () => [] },
  counts: { type: Object, default: () => ({}) },
  selectedDay: { type: String, default: '' },
  todayIso: { type: String, default: '' },
})
const emit = defineEmits(['pick'])
</script>

<style scoped>
.month-grid {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
}
.mg-head {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: var(--color-gray-50);
  border-bottom: 2px solid var(--color-gray-200);
}
.mg-wd {
  padding: 8px 0;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-gray-600);
}
.mg-body { display: flex; flex-direction: column; }
.mg-week { display: grid; grid-template-columns: repeat(7, 1fr); }
.mg-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-height: 76px;
  padding: 8px 4px;
  border: none;
  border-right: 1px solid var(--color-gray-100);
  border-bottom: 1px solid var(--color-gray-100);
  background: var(--color-white);
  cursor: pointer;
  transition: background 150ms;
}
.mg-week:last-child .mg-cell { border-bottom: none; }
.mg-cell:last-child { border-right: none; }
.mg-cell:hover { background: var(--color-gray-50); }
.mg-cell--out { background: var(--color-gray-100); }
.mg-cell--out .mg-day { color: var(--color-gray-500); }
.mg-cell--today { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.mg-cell--sel { box-shadow: inset 0 0 0 2px var(--color-accent); }
.mg-day {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-gray-800);
}
.mg-count {
  min-width: 20px;
  padding: 1px 6px;
  border-radius: var(--radius-full, 50%);
  background: var(--color-accent);
  color: var(--on-accent);
  font-size: 11px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
</style>
