<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Шаги тура по странице учеников: список, добавление по коду, детали.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'list',
    sel: '.students-page .list-panel',
    prefer: 'right',
    title: 'Выберите ученика',
    text: 'Слева — ваши ученики. Клик покажет настройки связи: ставку, скидку, самозапись и ссылки.',
    example: ['Иван Петров — 1500 ₽/час', 'Анна Смирнова — 2000 ₽/час'],
  },
  {
    id: 'add',
    sel: '.students-page .page-title-row .btn',
    prefer: 'bottom',
    title: 'Добавьте ученика по коду',
    text: 'Личный код ученик сообщает вам сам — списка всех учеников в системе нет.',
    example: ['Пример кода: ученик-017'],
  },
  {
    id: 'detail',
    sel: '.students-page .detail-panel',
    prefer: 'left',
    title: 'Правьте связь',
    text: '«Редактировать» меняет ставку, скидку, лимиты и ссылки. «Сбросить» возвращает значения по умолчанию из настроек.',
    example: ['Ставка: 1500 ₽/час', 'Скидка: 10% → итого 1350 ₽/час', 'Самозапись: разрешена'],
  },
]
</script>
