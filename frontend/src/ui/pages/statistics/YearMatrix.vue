<template>
  <section class="matrix-card">
    <div class="matrix-scroll">
      <div class="matrix" role="grid" aria-label="Динамика за год">
        <div class="mrow mrow--head">
          <button type="button" class="mcell mcell--corner" title="Отчёт за весь год" @click="emit('pick-year')">
            {{ year }}
          </button>
          <span v-for="d in 31" :key="d" class="mcell mcell--daynum">{{ d }}</span>
        </div>
        <div v-for="(row, m) in grid" :key="m" class="mrow">
          <button
            type="button" class="mcell mcell--month"
            :class="{ 'mcell--sel': selectedMonth === m }"
            :title="`Отчёт за ${monthShort(m)}`"
            @click="emit('pick-month', m)"
          >{{ monthShort(m) }}</button>
          <button
            v-for="(cell, di) in row" :key="di" type="button"
            class="mcell"
            :class="[
              cell.exists ? `shade-${shadeOf(cell)}` : 'mcell--void',
              cell.exists && cell.date === selectedDay ? 'mcell--sel' : '',
            ]"
            :disabled="!cell.exists"
            :title="cell.exists ? titleOf(cell) : ''"
            @click="cell.exists && emit('pick-day', cell.date)"
          >{{ cell.exists ? textOf(cell) : '' }}</button>
        </div>
      </div>
    </div>
    <p class="matrix-hint">Клик по дню — отчёт за день, по месяцу — за месяц, по году в углу — за год.</p>
  </section>
</template>

<script setup>
// Таблица-динамика «Год»: 12 строк-месяцев x 31 день, структура статична.
// Окраска — 5 оттенков синего шагом 20% от max видимых; 0/пусто не красим.
import { monthShort, cellValue, shadeLevel, fmtCellValue } from '../../../logic/utils/index.js'

const props = defineProps({
  year: { type: Number, required: true },
  grid: { type: Array, default: () => [] },
  metric: { type: String, default: 'conducted' },
  maxValue: { type: Number, default: 0 },
  selectedDay: { type: String, default: '' },
  selectedMonth: { type: Number, default: -1 },
})
const emit = defineEmits(['pick-day', 'pick-month', 'pick-year'])

function shadeOf(cell) {
  return shadeLevel(cellValue(cell.lessons, props.metric), props.maxValue)
}

function textOf(cell) {
  return fmtCellValue(cellValue(cell.lessons, props.metric), props.metric)
}

function titleOf(cell) {
  const t = textOf(cell)
  return t ? `${cell.date}: ${t}` : cell.date
}
</script>

<style scoped>
.matrix-card {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 14px; box-shadow: var(--shadow-sm); padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px;
}
.matrix-scroll { overflow-x: visible; }
.matrix { display: flex; flex-direction: column; }
.mrow { display: grid; grid-template-columns: 48px repeat(31, minmax(0, 1fr)); gap: 2px; }
.mrow + .mrow { margin-top: 2px; }
.mcell {
  min-height: 24px; min-width: 0; display: flex; align-items: center; justify-content: center;
  font-size: 11px; border-radius: 5px; border: 1px solid transparent;
  background: var(--color-gray-50); color: var(--color-gray-800);
  padding: 0 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
}
button.mcell { cursor: pointer; }
button.mcell:hover { border-color: var(--color-accent); }
button.mcell:disabled { cursor: default; }
.mcell--daynum {
  background: none; color: var(--color-gray-500); font-size: 10px; min-height: 18px;
}
.mcell--corner {
  background: var(--color-primary); color: var(--color-white);
  font-weight: 700; font-size: 12px;
}
.mcell--month {
  background: var(--color-gray-100); font-weight: 600; font-size: 11px;
  justify-content: flex-start; padding-left: 8px;
}
.mcell--void { background: var(--color-gray-100); opacity: 0.45; }
.mcell--sel { outline: 2px solid var(--color-accent); outline-offset: -2px; }
.shade-0 { background: var(--color-gray-50); color: var(--color-gray-400); }
.shade-1 { background: #dbe9f7; }
.shade-2 { background: #b3d1ee; }
.shade-3 { background: #84b4e3; color: #0f2f4d; }
.shade-4 { background: #4f93d3; color: #fff; }
.shade-5 { background: #1f6cb5; color: #fff; font-weight: 600; }
.matrix-hint { margin: 0; font-size: 12px; color: var(--color-gray-500); }
@media (max-width: 700px) {
  .matrix-card { padding: 8px 10px; }
  .mrow { grid-template-columns: 40px repeat(31, minmax(0, 1fr)); }
  .mcell { min-height: 20px; font-size: 10px; border-radius: 4px; }
  .mcell--daynum { font-size: 9px; min-height: 16px; }
  .mcell--month { font-size: 10px; padding-left: 6px; }
  .mcell--corner { font-size: 11px; }
  .matrix-hint { font-size: 11px; }
}
</style>
