<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Обучающий тур по странице броней: шаги, что показать и зачем.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'grid',
    sel: '.grid-body',
    prefer: 'top',
    title: 'Создайте бронь в один клик',
    text: 'Нажмите на пустую клетку — день и время сами подставятся в форму справа. Вводить часы вручную не нужно.',
    example: ['Пн 09:00–10:00 · Все'],
  },
  {
    id: 'legend',
    sel: '.legend',
    prefer: 'bottom',
    title: 'Читайте занятость по цвету',
    text: 'Цвет блока сразу показывает правило доступа. Зелёный — открыто всем.',
    example: ['Все — зелёный', 'Только избранные — жёлтый'],
  },
  {
    id: 'create',
    sel: '.side-col--wide .side-head',
    prefer: 'left',
    title: 'Готовьте несколько броней',
    text: 'Жмите + чтобы добавить формы, затем «Создать» — сохранятся все сразу.',
    example: ['Вт 10:00–11:00 · Все'],
  },
  {
    id: 'rule',
    sel: '.side-col--wide .rule-row',
    prefer: 'left',
    title: 'Откройте время только своим',
    text: 'Выберите «Только избранные» и отметьте учеников через +. Остальные это время не увидят.',
    example: ['Только избранные: Иван Петров'],
  },
  {
    id: 'info',
    sel: '.bookings-layout > .side-col:first-child .side-block',
    prefer: 'right',
    title: 'Меняйте созданное',
    text: 'Нажмите на бронь в списке слева, чтобы поправить время, правило или удалить её.',
    example: ['Пн 09:00–10:00 · Все'],
  },
]
</script>
