<template>
  <span class="st-chip" :class="isActive ? 'st-chip--active' : 'st-chip--inactive'" :title="title">{{ label }}</span>
</template>

<script setup>
// Статус ученика — только из его настроек (ACTIVE/INACTIVE).
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: 'ACTIVE' },
})

const isActive = computed(() => props.status !== 'INACTIVE')
const label = computed(() => (isActive.value ? 'Активен' : 'Неактивен'))
const title = computed(() => (isActive.value ? 'Ученик активен' : 'Ученик неактивен (настройки)'))
</script>

<style scoped>
.st-chip { display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 10px; white-space: nowrap; }
.st-chip--active { background: var(--rule-everyone-bg); color: var(--rule-everyone-text); }
.st-chip--inactive { background: var(--color-gray-100); color: var(--color-gray-600); }
</style>
