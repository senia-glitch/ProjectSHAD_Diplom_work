<template>
  <section class="weeks-card">
    <div class="weeks-head">
      <span v-for="m in 12" :key="m" class="weeks-month">{{ monthShort(m - 1) }}</span>
    </div>
    <div class="weeks-grid">
      <button
        v-for="w in weeks" :key="w.key" type="button"
        class="week"
        :class="{
          'week--sel': w.key === selectedKey,
          'week--span': w.fromM !== w.toM,
          'week--busy': busyKeys.has(w.key),
        }"
        :style="{ gridColumn: colOf(w) }"
        :title="`Неделя ${w.week}: ${w.from} — ${w.to}`"
        @click="emit('pick-week', w)"
      >
        <span class="week-num">{{ w.week }}</span>
        <span class="week-range">{{ fmtShortRange(w.from, w.to) }}</span>
      </button>
    </div>
    <p class="weeks-hint">Клик по карточке — отчёт за неделю. Неделя через стык месяцев — одна карточка на два столбца.</p>
  </section>
</template>

<script setup>
// Режим «Неделя»: первая строка — месяцы, в поле — карточки недель ISO Пн–Вс.
// На карточке только номер и короткий диапазон дат (без мини-цифр).
import { monthShort, fmtShortRange, weekSpan } from '../../../logic/utils/index.js'

const props = defineProps({
  year: { type: Number, required: true },
  weeks: { type: Array, default: () => [] },
  selectedKey: { type: String, default: '' },
  // Ключи недель, на которых есть уроки, — такие карточки подсвечены.
  busyKeys: { type: Set, default: () => new Set() },
})

function colOf(w) {
  const s = weekSpan(props.year, w)
  return `${s.start} / span ${s.span}`
}
const emit = defineEmits(['pick-week'])
</script>

<style scoped>
.weeks-card {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 14px; box-shadow: var(--shadow-sm); padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px;
}
.weeks-head, .weeks-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 4px; }
.weeks-month { font-size: 10px; font-weight: 700; color: var(--color-gray-700); text-align: center; overflow: hidden; text-overflow: ellipsis; }
.weeks-grid { grid-auto-flow: row dense; }
.week {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 6px 2px; border: 1px solid var(--color-gray-200); border-radius: 8px;
  background: var(--color-gray-50); cursor: pointer; min-width: 0; overflow: hidden;
}
.week:hover { border-color: var(--color-accent); }
.week--sel { outline: 2px solid var(--color-accent); outline-offset: -2px; background: var(--color-accent-50); }
.week-num { font-size: 12px; font-weight: 400; color: var(--color-gray-800); white-space: nowrap; }
.week-range { font-size: 10px; color: var(--color-gray-600); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
/* Неделя на два месяца: номер слева, диапазон справа в одну строку. */
.week--span { flex-direction: row; justify-content: space-between; padding: 6px 10px; }
/* Неделя с уроками подсвечена. */
.week--busy { border-color: var(--color-accent); background: var(--color-accent-50); }
.weeks-hint { margin: 0; font-size: 12px; color: var(--color-gray-500); }
</style>
