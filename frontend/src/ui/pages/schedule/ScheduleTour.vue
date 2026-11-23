<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Обучающий тур по странице расписания: что показать и зачем.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'grid',
    sel: '.grid-body',
    prefer: 'top',
    title: 'Выберите урок кликом',
    text: 'Слева откроются детали: время, участники, изменение и удаление. Бледные блоки — ваши шаблоны броней (галочка «Брони» над сеткой).',
    example: ['Ср 10:00–11:00 · Иван Петров', 'Пт 12:00–13:00 · группа (3)'],
  },
  {
    id: 'weeknav',
    sel: '.calendar-nav',
    prefer: 'bottom',
    title: 'Листайте недели',
    text: 'Стрелки двигают календарь, «Сегодня» возвращает к текущей неделе.',
    example: ['‹ 12–18 мая › · «Сегодня»'],
  },
  {
    id: 'create',
    sel: '.side-col--wide .side-head',
    prefer: 'left',
    title: 'Готовьте уроки пачками',
    text: 'Плюс — новая форма: конкретные даты или дни недели с периодичностью. «Создать» сохраняет всё сразу.',
    example: ['24.09 Ср 09:00–10:00', 'Пн/Ср/Пт · 4 недели'],
  },
  {
    id: 'preview',
    sel: '.grid-body .block--preview',
    prefer: 'bottom',
    title: 'Проверяйте черновик',
    text: 'Полосатые блоки — уроки из формы. После «Создать» они станут настоящими.',
  },
  {
    id: 'info',
    sel: '.schedule-layout > .side-col:first-child .side-block',
    prefer: 'right',
    title: 'Меняйте состав урока',
    text: 'В «Изменить» добавьте ученика: без «группового» — один селект, с ним — строки. «Сохранить» применяет всё разом.',
    example: ['Участники: Иван, Анна', 'Время: Ср 10:00–11:00'],
  },
]
</script>
