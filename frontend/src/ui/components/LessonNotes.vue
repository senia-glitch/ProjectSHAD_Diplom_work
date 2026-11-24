<template>
  <div v-if="noteText || absenceText || lines.length" class="lesson-notes">
    <p v-if="absenceText" class="lesson-note lesson-note--absence" role="note">
      <UiIcon name="clock" /> <span>{{ absenceText }}</span>
    </p>
    <p v-if="noteText" class="lesson-note" :class="`lesson-note--${note?.status?.toLowerCase()}`" role="note">
      <UiIcon name="info" /> <span>{{ noteText }}</span>
    </p>
    <details v-if="showHistory && lines.length" class="lesson-history">
      <summary>История урока ({{ lines.length }})</summary>
      <ol>
        <li v-for="(line, i) in lines" :key="i"><time>{{ line.at }}</time> {{ line.text }}</li>
      </ol>
    </details>
  </div>
</template>

<script setup>
// Пометки урока: кто/когда/почему изменил статус, отпуск репетитора, история.
// Только показ: данные — пропсами (тексты собирает logic/utils/lesson.js).
import { computed } from 'vue'
import UiIcon from './UiIcon.vue'
import { describeStatusNote, describeAbsence, statusHistoryLines } from '../../logic/utils/index.js'

const props = defineProps({
  note: { type: Object, default: null },
  absence: { type: Object, default: null },
  history: { type: Array, default: () => [] },
  showHistory: { type: Boolean, default: false },
})

const noteText = computed(() => describeStatusNote(props.note))
const absenceText = computed(() => describeAbsence(props.absence))
const lines = computed(() => statusHistoryLines(props.history))
</script>

<style scoped>
.lesson-notes { display: grid; gap: 8px; }
.lesson-note {
  display: flex; gap: 8px; align-items: flex-start; margin: 0;
  padding: 8px 10px; border-radius: var(--r-sm, 8px);
  border: 1px solid var(--line, var(--color-gray-300)); background: var(--surface-2, transparent);
  font-size: 13px; line-height: 1.45; color: var(--text, inherit);
}
.lesson-note :deep(svg) { flex: none; width: 16px; height: 16px; margin-top: 1px; }
.lesson-note--cancelled, .lesson-note--rejected { border-color: var(--rule-nobody-border, var(--danger)); }
.lesson-note--pending { border-color: var(--rule-only-border, #d4a72c); }
.lesson-note--absence { border-color: var(--rule-except-border, #c77d3a); }
.lesson-history { font-size: 13px; color: var(--muted, var(--color-gray-600)); }
.lesson-history summary { cursor: pointer; }
.lesson-history ol { margin: 6px 0 0; padding-left: 18px; display: grid; gap: 4px; }
.lesson-history time { font-variant-numeric: tabular-nums; margin-right: 6px; }
</style>
