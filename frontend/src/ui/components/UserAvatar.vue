<template>
  <span class="user-avatar" :style="{ '--ua-size': `${size}px` }" aria-hidden="true">
    <img v-if="url && !failed" :src="url" alt="" loading="lazy" referrerpolicy="no-referrer" @error="failed = true" />
    <span v-else>{{ letter }}</span>
  </span>
</template>

<script setup>
// Аватар пользователя: фото по внешней ссылке, без фото или при ошибке загрузки — первая буква имени.
import { computed, ref, watch } from 'vue'
import { safeUrl } from '../../logic/utils/index.js'

const props = defineProps({
  src: { type: String, default: '' },
  name: { type: String, default: '' },
  size: { type: Number, default: 36 },
})
const failed = ref(false)
const url = computed(() => safeUrl(props.src || '') || '')
const letter = computed(() => (props.name || '?').trim().slice(0, 1).toUpperCase() || '?')
watch(() => props.src, () => { failed.value = false })
</script>

<style scoped>
.user-avatar {
  width: var(--ua-size); height: var(--ua-size); flex: none; display: inline-grid; place-items: center;
  border-radius: 50%; overflow: hidden; background: var(--accent-soft); color: var(--accent);
  font-weight: 600; font-size: calc(var(--ua-size) * .42); line-height: 1;
}
.user-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
</style>
