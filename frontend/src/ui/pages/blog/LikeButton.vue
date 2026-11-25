<template>
  <button
    type="button"
    class="like-btn"
    :class="{ on: liked }"
    :aria-pressed="liked"
    :aria-label="liked ? `Убрать отметку «нравится», всего ${count}` : `Нравится, всего ${count}`"
    :disabled="busy"
    @click="$emit('toggle')"
  >
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M12 20.5s-7.5-4.4-7.5-10A4.3 4.3 0 0 1 12 7.8a4.3 4.3 0 0 1 7.5 2.7c0 5.6-7.5 10-7.5 10Z"
            :fill="liked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
    </svg>
    <span>{{ count }}</span>
  </button>
</template>

<script setup>
// «Нравится» для записи блога: только показ, нажатие обрабатывает страница.
defineProps({
  count: { type: Number, default: 0 },
  liked: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
defineEmits(['toggle'])
</script>

<style scoped>
.like-btn { display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 12px; border-radius: 999px; border: 1px solid var(--line-strong); background: var(--surface); color: var(--muted); font: 500 13.5px var(--sans); cursor: pointer; transition: color var(--t), border-color var(--t), transform var(--t); }
.like-btn:hover:not(:disabled) { color: var(--danger); border-color: var(--danger); }
.like-btn.on { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 60%, var(--line)); background: color-mix(in srgb, var(--danger) 10%, transparent); }
.like-btn:active:not(:disabled) { transform: scale(.94); }
.like-btn:disabled { opacity: .6; cursor: wait; }
@media (prefers-reduced-motion: reduce) { .like-btn { transition: none; } .like-btn:active:not(:disabled) { transform: none; } }
</style>
