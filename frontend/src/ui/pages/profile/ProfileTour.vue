<template>
  <TourOverlay :steps="STEPS" @close="emit('close')" />
</template>

<script setup>
// Шаги тура по странице профиля: карточка, форма данных.
// Движок — общий TourOverlay из UI-кита.
import { TourOverlay } from '../../components/index.js'

const emit = defineEmits(['close'])

const STEPS = [
  {
    id: 'card',
    sel: '.profile-page .profile-header',
    prefer: 'bottom',
    title: 'Ваш профиль',
    text: 'Карточка показывает имя, роль и ваш личный код — кодом делятся для связи.',
  },
  {
    id: 'form',
    sel: '.profile-page .profile-form',
    prefer: 'top',
    title: 'Личные данные',
    text: 'Имя и email для связи. «Сохранить» применяет изменения сразу.',
  },
]
</script>
