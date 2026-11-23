<template>
  <!-- Общий каркас публичных страниц: шапка + контентные секции.
       Данных и вызовов не имеет — только разметка (§10: blocks без logic). -->
  <div class="public-page">
    <div class="page-header">
      <div class="page-title-row">
        <h1 class="page-title">{{ title }}</h1>
      </div>
      <p class="page-desc">{{ subtitle }}</p>
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<style scoped>
.public-page { display: flex; flex-direction: column; }
</style>
