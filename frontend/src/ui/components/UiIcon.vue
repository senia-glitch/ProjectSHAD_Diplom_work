<template>
  <svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path :d="paths[name] || paths.calendar" />
  </svg>
</template>

<script setup>
defineProps({ name: { type: String, default: 'calendar' } })
const paths = {
  calendar: 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2m3 10h2m4 0h2m-8 4h2',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2',
  users: 'M15 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M3 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2m-1-18a4 4 0 0 1 0 8m3 4a6 6 0 0 1 2 4v2',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',
  clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0M12 6v6l4 2',
  wallet: 'M20 7H5a2 2 0 0 1 0-4h13v4m2 0a1 1 0 0 1 1 1v12H5a2 2 0 0 1-2-2V5m18 7h-5v4h5m-4-2h.01',
  chart: 'M4 3v18h17M8 16v-5m5 5V6m5 10v-8',
  shield: 'M12 2 3 6v6c0 6 9 10 9 10s9-4 9-10V6l-9-4m-4 10 3 3 5-6',
  sun: 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5',
  moon: 'M21 13a9 9 0 0 1-10-10 9 9 0 1 0 10 10',
  plus: 'M12 5v14M5 12h14',
  arrowLeft: 'M19 12H5m7-7-7 7 7 7',
  arrowRight: 'M5 12h14m-7-7 7 7-7 7',
  info: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0M12 11v6m0-10h.01',
  check: 'M5 12l4 4L19 6',
}
</script>

<style scoped>
.ui-icon { width: 20px; height: 20px; flex-shrink: 0; display: block; }
</style>
