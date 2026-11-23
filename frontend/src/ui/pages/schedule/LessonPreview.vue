<template>
  <span class="pick-lbl">Предпросмотр ({{ items.length }})</span>
  <div v-if="skipped > 0" class="pick-empty">Прошедшее время в список не попадает: пропущено {{ skipped }} — уроки в прошлом не создаются</div>
  <div v-if="hasInput && !items.length" class="pick-empty">Нет корректных уроков — проверьте даты и время</div>
  <div v-for="it in items" :key="it.key" class="pv-row">
    <span>{{ fmtPreview(it.start, it.end) }}</span>
    <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать из списка" @click="dropItem(it.key)">−</button>
  </div>
</template>

<script setup>
// Предпросмотр одной формы. Ручные удаления пишут прямо во вложенное
// поле слота (dropped) — их забывает вотчер настроек в LessonCreator.
import { computed } from 'vue'
import { previewItems, skippedPastCount, hasSlotInput, fmtPreview } from '../../../logic/utils/index.js'

const props = defineProps({
  slot: { type: Object, required: true },
})

const items = computed(() => previewItems(props.slot))
const skipped = computed(() => skippedPastCount(props.slot))
const hasInput = computed(() => hasSlotInput(props.slot))

function dropItem(key) {
  const slot = props.slot
  slot.dropped = [...(slot.dropped || []), key]
}
</script>

