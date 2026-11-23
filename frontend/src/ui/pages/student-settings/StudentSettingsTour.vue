<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Шаги тура по странице настроек ученика.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'main',
    sel: '.student-settings-page .card',
    prefer: 'bottom',
    title: 'Основные параметры',
    text: 'Статус, часовой пояс и вид расписания. Неактивный статус блокирует самозапись на уроки.',
  },
  {
    id: 'save',
    sel: '.student-settings-page .save-bar',
    prefer: 'top',
    title: 'Сохранить',
    text: '«Сохранить» применяет всё разом.',
  },
]
</script>
