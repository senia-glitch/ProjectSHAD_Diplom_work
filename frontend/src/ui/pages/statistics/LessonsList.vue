<template>
  <div class="lessons-list">
    <div v-if="!lessons.length" class="list-empty">
      <b>{{ emptyTitle }}</b>
      <span>{{ emptyHint }}</span>
    </div>
    <template v-else>
      <div v-for="day in days" :key="day.date" class="day-group">
        <div class="day-head">{{ day.label }}</div>
        <LessonRow
          v-for="lesson in day.lessons" :key="lesson.lesson_id"
          :lesson="lesson" :expanded="expandedId === lesson.lesson_id"
          @toggle="expandedId = expandedId === lesson.lesson_id ? null : lesson.lesson_id"
          @toggle-pay="emit('toggle-pay', $event)"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import LessonRow from './LessonRow.vue'

const props = defineProps({
  lessons: { type: Array, default: () => [] },
  emptyTitle: { type: String, default: 'За период уроков нет' },
  emptyHint: { type: String, default: 'Попробуйте изменить период или создать урок в расписании.' },
})
const emit = defineEmits(['toggle-pay'])

const expandedId = ref(null)

const DAYS_FULL = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

function dayLabel(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  return `${d} ${MONTHS[m - 1]}, ${DAYS_FULL[dt.getDay()]}`
}

const days = computed(() => {
  const map = new Map()
  for (const lesson of props.lessons) {
    if (!map.has(lesson.date)) map.set(lesson.date, { date: lesson.date, label: dayLabel(lesson.date), lessons: [] })
    map.get(lesson.date).lessons.push(lesson)
  }
  return [...map.values()]
})
</script>

<style scoped>
.lessons-list { display: flex; flex-direction: column; }
.list-empty { display: flex; flex-direction: column; gap: 4px; padding: 20px; text-align: center; color: var(--color-gray-500); font-size: 13px; }
.list-empty b { color: var(--color-gray-700); }
.day-group { display: flex; flex-direction: column; border: 1px solid var(--color-gray-200); border-radius: 8px; padding: 4px 12px 8px; background: var(--color-white); }
.day-group + .day-group { margin-top: 12px; }
.day-head { font-size: 13px; font-weight: 600; color: var(--color-gray-800); padding: 8px 4px; border-bottom: 1px solid var(--color-gray-100); }
</style>
