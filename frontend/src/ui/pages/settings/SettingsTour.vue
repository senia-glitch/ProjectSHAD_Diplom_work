<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Шаги тура по странице настроек: самозапись, ссылки, сохранение.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'modes',
    sel: '.settings-page .toggle-row',
    prefer: 'bottom',
    title: 'Самозапись учеников',
    text: '«Да» — запись открыта всем. Иначе работает белый список, а сохранение раскидывает режим на всех учеников.',
    example: ['Да — всем', 'Нет — только белый список'],
  },
  {
    id: 'links',
    sel: '.settings-page .links-list',
    prefer: 'left',
    title: 'Ссылки для новых учеников',
    text: 'Новые связи скопируют их себе и дальше живут независимо. Только https://.',
    example: ['Zoom — https://zoom.us/j/123', 'Материалы — https://docs.example/abc'],
  },
  {
    id: 'save',
    sel: '.settings-page .save-bar',
    prefer: 'top',
    title: 'Сохранить и сбросить',
    text: '«Сохранить» применяет всё разом. «Сбросить» возвращает скидку, пояс, статус и вид расписания к начальным.',
    example: ['Скидка → 0%', 'Пояс → UTC+0', 'Вид интерфейса → минималистичный'],
  },
]
</script>
