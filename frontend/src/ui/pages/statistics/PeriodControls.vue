<template>
  <div class="period-controls" :class="{ 'period-controls--bare': bare }">
    <span v-if="!bare" class="period-cap">Период</span>
    <div class="seg" role="tablist" aria-label="Пресет периода">
      <button
        v-for="p in presets" :key="p.value" type="button"
        :class="filters.preset === p.value ? 'seg-on' : ''"
        @click="emit('update', { preset: p.value })"
      >{{ p.label }}</button>
    </div>
    <MonthPicker
      v-if="filters.preset === 'month'"
      :model-value="filters.month"
      @update="emit('update', { month: $event })"
    />
    <DatePicker
      v-if="filters.preset === 'week'"
      :model-value="filters.weekAnchor"
      @update="emit('update', { weekAnchor: $event })"
    />
    <template v-if="filters.preset === 'custom'">
      <DatePicker :model-value="filters.customFrom" @update="emit('update', { customFrom: $event })" />
      <span class="range-dash">—</span>
      <DatePicker :model-value="filters.customTo" @update="emit('update', { customTo: $event })" />
    </template>
  </div>
</template>

<script setup>
// Выбор периода внутри блоков «Уроки» и «Ученики»:
// Год/Месяц/Неделя/Период влияют на эти блоки, к Динамике не относятся.
import DatePicker from './DatePicker.vue'
import MonthPicker from './MonthPicker.vue'

defineProps({
  filters: { type: Object, required: true },
  // В сайдбаре: без своего заголовка и нижнего отступа (даёт секция).
  bare: { type: Boolean, default: false },
})
const emit = defineEmits(['update'])

const presets = [
  { value: 'year', label: 'Год' },
  { value: 'month', label: 'Месяц' },
  { value: 'week', label: 'Неделя' },
  { value: 'custom', label: 'Период' },
]
</script>

<style scoped>
.period-controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.period-controls--bare { margin-bottom: 0; }
.period-cap {
  font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--color-gray-500); white-space: nowrap;
}
.seg { display: flex; background: var(--color-gray-100); border-radius: 9px; padding: 3px; gap: 2px; }
.seg button {
  border: none; background: none; cursor: pointer; font-size: 12px; font-weight: 500;
  color: var(--color-gray-600); padding: 6px 12px; border-radius: 7px;
}
.seg button:hover { color: var(--color-gray-800); }
.seg button.seg-on { background: var(--color-white); color: var(--color-gray-800); box-shadow: var(--shadow-sm); }
.range-dash { color: var(--color-gray-400); }
</style>
