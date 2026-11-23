<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Шаги тура по странице репетиторов: список, добавление по коду, детали.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'code',
    sel: '.tutors-page .my-code',
    prefer: 'bottom',
    title: 'Ваш личный код',
    text: 'Этим кодом делятся с репетитором — он добавит вас по коду у себя.',
  },
  {
    id: 'list',
    sel: '.tutors-page .list-panel',
    prefer: 'right',
    title: 'Выберите репетитора',
    text: 'Слева — ваши репетиторы. Клик покажет настройки связи: ставку, скидку и самозапись.',
  },
  {
    id: 'add',
    sel: '.tutors-page .page-title-row .btn',
    prefer: 'bottom',
    title: 'Добавьте репетитора по коду',
    text: 'Личный код репетитор сообщает вам сам — списка всех репетиторов в системе нет.',
  },
  {
    id: 'detail',
    sel: '.tutors-page .detail-panel',
    prefer: 'left',
    title: 'Смотрите связь',
    text: 'Детали показывают ставку, скидку, самозапись и итоговую цену для вас.',
  },
]
</script>
