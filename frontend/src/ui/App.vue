<template>
  <!-- Доска живёт в keep-alive: переходы по разделам не разрывают соединение.
       Ключ — id доски: другая доска открывается новым экземпляром (max 1 — старая закрывается).
       После выхода из аккаунта список пуст: Vue выбрасывает доску из кэша и закрывает её соединение. -->
  <router-view v-slot="{ Component, route }">
    <keep-alive :include="cached" :max="1">
      <component :is="Component" :key="route.name === 'board' ? `board-${route.params.id}` : undefined" />
    </keep-alive>
  </router-view>
</template>

<script setup>
import { computed } from 'vue'
import { useUser } from './composables/index.js'

const { isLoggedIn } = useUser()
const cached = computed(() => (isLoggedIn.value ? ['BoardPage'] : []))
</script>
