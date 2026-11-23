<template>
  <span class="pick-lbl">Предпросмотр ({{ validCount }})</span>
  <div v-if="loading" class="pick-empty">Загрузка свободных окон…</div>
  <template v-else>
    <div v-if="skipped > 0" class="pick-empty">Прошедшее время в список не попадает: пропущено {{ skipped }} — уроки в прошлом не создаются</div>
    <div v-if="hasInput && !items.length" class="pick-empty">Нет корректных уроков — проверьте даты и время</div>
    <div v-for="it in items" :key="it.key" class="pv-row" :class="{ 'pv-row--bad': !it.ok }">
      <span v-if="it.ok">{{ fmtPreview(it.start, it.end) }}</span>
      <span v-else>{{ fmtPreviewSafe(it) }} — {{ reasonText(it.reason) }}</span>
      <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать из списка" @click="dropItem(it.key)" aria-label="Убрать из списка">−</button>
    </div>
    <div v-if="invalidCount > 0" class="pick-empty">Вне окон или не по шагу: {{ invalidCount }} — при создании пропускаются</div>
  </template>
</template>

<script setup>
// Предпросмотр записи ученика: валидные строки как обычно,
// невалидные — с причиной (вне окон / не по сетке / длительность).
// Ручные удаления пишут в slot.dropped, их забывает вотчер формы.
import { computed } from 'vue'
import { buildStudentPreview, fmtPreview } from '../../../logic/utils/index.js'

const props = defineProps({
  slot: { type: Object, required: true },
  windows: { type: Array, default: () => [] },
  step: { type: Number, default: 60 },
  loading: { type: Boolean, default: false },
})

const built = computed(() => buildStudentPreview(props.slot, props.windows, props.step))
const items = computed(() => built.value.items)
const validCount = computed(() => items.value.filter((x) => x.ok).length)
const invalidCount = computed(() => items.value.filter((x) => !x.ok).length)
const skipped = computed(() => built.value.skippedPast)
const hasInput = computed(() => {
  if (props.slot.mode === 'dates') return (props.slot.dates || []).length > 0
  return Object.values(props.slot.weekdays || {}).some((c) => c.on)
})

function reasonText(reason) {
  if (reason === 'outside') return 'вне свободных окон'
  if (reason === 'off-grid') return 'старт не по сетке шага'
  if (reason === 'bad-duration') return 'длительность не подходит'
  return 'не подходит'
}

function fmtPreviewSafe(it) {
  try {
    return fmtPreview(it.start, it.end)
  } catch {
    return it.start
  }
}

function dropItem(key) {
  const slot = props.slot
  slot.dropped = [...(slot.dropped || []), key]
}
</script>

<style scoped>
.pv-row--bad { opacity: 0.75; }
.pv-row--bad span { color: var(--color-danger); }
</style>
