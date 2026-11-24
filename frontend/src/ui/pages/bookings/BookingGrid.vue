<template>
  <div class="grid-wrap">
    <div v-if="narrow" class="days-nav">
      <button type="button" class="btn-nav" aria-label="Предыдущие дни" :disabled="dayStart === 0" @click="shiftDays(-1)"><UiIcon name="arrowLeft" /></button>
      <span class="days-range">{{ weekdayShort[visibleDays[0]] }} — {{ weekdayShort[visibleDays[visibleDays.length - 1]] }}</span>
      <button type="button" class="btn-nav" aria-label="Следующие дни" :disabled="dayStart >= WEEKDAY_ORDER.length - NARROW_DAYS" @click="shiftDays(1)"><UiIcon name="arrowRight" /></button>
    </div>
    <p class="grid-hint">Прокрутите сетку, чтобы увидеть остальные дни и часы.</p>
    <div class="grid-scroll" role="region" tabindex="0" aria-label="Сетка недели. Прокрутите, чтобы увидеть остальные дни и часы.">
    <div class="grid-container" :style="{ '--days': visibleDays.length }" :class="{ 'grid-container--short': narrow }">
      <div class="grid-header">
        <div class="corner"></div>
        <div v-for="day in visibleDays" :key="day" class="day-head">{{ weekdayShort[day] }}</div>
      </div>
      <div class="grid-body">
        <div class="time-col">
          <div v-for="h in 24" :key="h" class="time-slot">
            <span class="time-lbl">{{ String(h - 1).padStart(2, '0') }}:00</span>
          </div>
        </div>
        <div v-for="day in visibleDays" :key="day" class="day-col" @click="onGridClick(day, $event)">
          <div v-for="h in 24" :key="h" class="hour-cell"></div>
          <div
            v-for="b in bookingsOfDay(day)"
            :key="b.id"
            class="block"
            :class="[`block--${b.access_rule.toLowerCase()}`, { 'block--sel': selectedId === b.id }]"
            :style="blockStyle(b)"
            @click.stop="emit('select-booking', b)"
          ><span class="block-txt">{{ b.start_time }}–{{ b.end_time }}</span></div>
          <div
            v-for="p in previewOfDay(day)"
            :key="p.id"
            class="block block--preview"
            :style="blockStyle(p)"
            title="Предпросмотр — ещё не создан"
          ><span class="block-txt">{{ p.start_time }}–{{ p.end_time }}</span></div>
        </div>
      </div>
    </div>
    </div>
    <div class="legend">
      <div v-for="(label, rule) in RULE_LABELS" :key="rule" class="legend-i">
        <span class="legend-d" :class="`legend-d--${rule.toLowerCase()}`"></span>{{ label }}
      </div>
    </div>
  </div>
</template>

<script setup>
// Сетка недели: только отображение. Брони — пропсом, клики — эмитами.
// Пиксельная математика клика — здесь (координаты вида).
import { toMin, blockGeometry } from '../../../logic/utils/index.js'
import { WEEKDAY_ORDER, WEEKDAY_SHORT, RULE_LABELS, GRID_H } from '../../../logic/constants/index.js'
import { logState } from '../../../logic/logger/index.js'
import { computed, ref } from 'vue'
import { UiIcon } from '../../components/index.js'
import { useNarrowScreen, NARROW_DAYS } from '../../composables/index.js'

// На телефоне — окно из 3 дней недели со стрелками (неделя целиком слишком широкая).
const narrow = useNarrowScreen()
const dayStart = ref(0)
const visibleDays = computed(() => (narrow.value ? WEEKDAY_ORDER.slice(dayStart.value, dayStart.value + NARROW_DAYS) : WEEKDAY_ORDER))
function shiftDays(direction) {
  const max = WEEKDAY_ORDER.length - NARROW_DAYS
  dayStart.value = Math.max(0, Math.min(max, dayStart.value + direction * NARROW_DAYS))
}

const props = defineProps({
  bookings: { type: Array, default: () => [] },
  previewBookings: { type: Array, default: () => [] },
  selectedId: { type: [Number, String], default: null },
})
const emit = defineEmits(['select-booking', 'grid-click'])

const weekdayShort = WEEKDAY_SHORT

function bookingsOfDay(day) {
  return props.bookings.filter((b) => b.weekday === day)
}

function previewOfDay(day) {
  return props.previewBookings.filter((b) => b.weekday === day)
}

function blockStyle(b) {
  return blockGeometry(b.start_time, b.end_time, GRID_H)
}

function onGridClick(day, ev) {
  const rect = ev.currentTarget.getBoundingClientRect()
  const pct = (ev.clientY - rect.top) / rect.height
  const raw = Math.round((pct * 1440) / 5) * 5
  const clamped = Math.max(0, Math.min(raw, 1435))
  const h = Math.floor(clamped / 60)
  const m = clamped % 60
  const endMin = Math.min(clamped + 60, 1439)
  const startTime = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
  const endTime = `${String(Math.floor(endMin / 60)).padStart(2, '0')}:${String(endMin % 60).padStart(2, '0')}`
  emit('grid-click', { day, startTime, endTime })
  logState('bookings', 'gridClick', { day, start: startTime, end: endTime })
}
</script>

<style scoped>
/* === GRID === */
.grid-wrap { flex: 1; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.grid-container {
  background: var(--color-white); border-radius: 12px; border: 1px solid var(--color-gray-200);
  display: flex; flex-direction: column; overflow: hidden; flex: 1;
}
.grid-header {
  display: grid; grid-template-columns: 44px repeat(var(--days, 7), 1fr);
  background: var(--color-gray-50); border-bottom: 2px solid var(--color-gray-200); flex-shrink: 0;
}
.corner { border-right: 1px solid var(--color-gray-200); }
.day-head {
  text-align: center; padding: 8px 2px; font-size: 13px; font-weight: 600;
  color: var(--color-gray-700); border-right: 1px solid var(--color-gray-100);
}
.day-head:last-child { border-right: none; }

.grid-body {
  display: grid; grid-template-columns: 44px repeat(var(--days, 7), 1fr);
  height: 600px; overflow: hidden;
}
.time-col { border-right: 1px solid var(--color-gray-200); }
.time-slot {
  height: 25px; display: flex; align-items: flex-start; justify-content: flex-end;
  padding: 0 4px; border-bottom: 1px solid var(--color-gray-100);
}
.time-lbl {
  font-size: 10px; color: var(--color-gray-500); font-variant-numeric: tabular-nums;
  position: relative; top: -6px; background: var(--color-white); padding: 0 2px;
}
/* Подпись самого верхнего часа не уезжает вверх под шапку таблицы. */
.time-col .time-slot:first-child .time-lbl { top: 0; }
.day-col { position: relative; border-right: 1px solid var(--color-gray-100); }
.day-col:last-child { border-right: none; }
.hour-cell { height: 25px; border-bottom: 1px solid var(--color-gray-100); cursor: pointer; }
.hour-cell:hover { background: var(--color-accent-5); }

.block {
  position: absolute; left: 2px; right: 2px; border-radius: 5px;
  cursor: pointer; z-index: 10; display: flex; align-items: center;
  justify-content: center; transition: box-shadow 120ms, opacity 120ms;
  border: 1px solid transparent; overflow: hidden;
}
.block:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.18); z-index: 20; }
.block--sel { box-shadow: 0 0 0 2px var(--color-accent); z-index: 25; }
/* Превью создаваемых броней: серая штриховка поверх реальных.
   Некликабельные — клики проходят сквозь на сетку. */
.block--preview {
  background: repeating-linear-gradient(45deg, rgba(134,142,150,0.28) 0 4px, rgba(134,142,150,0.10) 4px 8px);
  color: var(--color-gray-700); border: 1px dashed var(--color-gray-600);
  pointer-events: none; z-index: 15;
}
.block-txt {
  font-size: 11px; font-weight: 600; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; padding: 0 3px; line-height: 1.2;
}
.block--everyone { background: var(--rule-everyone-bg); color: var(--rule-everyone-text); border-color: var(--rule-everyone-border); }
.block--only { background: var(--rule-only-bg); color: var(--rule-only-text); border-color: var(--rule-only-border); }
.block--all_except { background: var(--rule-all-except-bg); color: var(--rule-all-except-text); border-color: var(--rule-all-except-border); }
.block--nobody { background: var(--rule-nobody-bg); color: var(--rule-nobody-text); border-color: var(--rule-nobody-border); }

.legend { display: flex; gap: 16px; flex-wrap: wrap; }
.legend-i { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--color-gray-700); }
.legend-d { width: 12px; height: 12px; border-radius: 3px; }
.legend-d--everyone { background: var(--rule-everyone-bg); border: 1px solid var(--rule-everyone-border); }
.legend-d--only { background: var(--rule-only-bg); border: 1px solid var(--rule-only-border); }
.legend-d--all_except { background: var(--rule-all-except-bg); border: 1px solid var(--rule-all-except-border); }
.legend-d--nobody { background: var(--rule-nobody-bg); border: 1px solid var(--rule-nobody-border); }

.grid-scroll { overflow: auto; max-height: 680px; border: 1px solid var(--line); border-radius: var(--radius-lg); scrollbar-width: thin; scrollbar-color: var(--line-strong) var(--surface); }
.grid-container { min-width: 560px; border: 0; border-radius: 0; }
.grid-container--short { min-width: 0; }
.days-nav { display: flex; align-items: center; gap: 8px; }
.days-range { font-weight: 600; min-width: 80px; text-align: center; }
.btn-nav { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); color: var(--text); cursor: pointer; }
.btn-nav:disabled { opacity: .4; cursor: default; }
.btn-nav :deep(svg) { width: 18px; height: 18px; }
.grid-header { position: sticky; top: 0; z-index: 30; border-bottom-width: 1px; }
.grid-header, .grid-body { grid-template-columns: 48px repeat(var(--days, 7), minmax(0, 1fr)); }
.time-lbl { font-size: 10px; color: var(--muted); }
.day-head { padding-block: 12px; }
.day-head--today { color: var(--accent); background: var(--accent-soft); }
.day-num { font-size: 17px; }
@media (max-width: 600px) {
  .grid-scroll { max-height: 520px; }
  .calendar-nav { gap: 8px; }
  .week-range { font-size: 13px; }
}

.grid-hint { display: none; font-size: 11px; color: var(--muted); }
@media (max-width: 600px) { .grid-hint { display: block; } }
</style>
