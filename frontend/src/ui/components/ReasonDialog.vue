<template>
  <dialog ref="dialogRef" class="reason-dialog" :aria-labelledby="titleId" @close="onClose">
    <form method="dialog" @submit.prevent="submit">
      <h2 :id="titleId" class="reason-title">{{ title }}</h2>
      <p v-if="text" class="reason-text">{{ text }}</p>
      <label class="reason-label">
        Причина <span class="reason-hint">(необязательно)</span>
        <textarea v-model="reason" rows="3" maxlength="500" :placeholder="placeholder"></textarea>
      </label>
      <p v-if="error" class="reason-error" role="alert">{{ error }}</p>
      <div class="reason-actions">
        <button type="button" class="btn btn--gry btn--sm" :disabled="busy" @click="close">Назад</button>
        <button type="submit" class="btn btn--sm" :class="danger ? 'btn--dan' : 'btn--pri'" :disabled="busy">
          {{ busy ? 'Сохранение…' : confirmLabel }}
        </button>
      </div>
    </form>
  </dialog>
</template>

<script setup>
// Подтверждение действия над уроком с необязательной причиной (отмена, отклонение).
// Открытие — open(); решение — событие confirm(reason); ошибку показывает родитель через проп.
import { ref } from 'vue'

defineProps({
  title: { type: String, required: true },
  text: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Подтвердить' },
  placeholder: { type: String, default: 'Например: заболел, перенесём на следующую неделю' },
  danger: { type: Boolean, default: true },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['confirm', 'closed'])

const dialogRef = ref(null)
const reason = ref('')
const titleId = `reason-${Math.random().toString(36).slice(2, 8)}`

function open() {
  reason.value = ''
  dialogRef.value?.showModal()
}
function close() {
  dialogRef.value?.close()
}
function submit() {
  emit('confirm', reason.value.trim())
}
function onClose() {
  emit('closed')
}

defineExpose({ open, close })
</script>

<style scoped>
.reason-dialog {
  margin: auto; width: min(440px, calc(100vw - 32px)); padding: 20px;
  border: 1px solid var(--line, var(--color-gray-300)); border-radius: var(--r-md, 12px);
  background: var(--surface, var(--color-white)); color: var(--text, inherit);
}
.reason-dialog::backdrop { background: rgba(0, 0, 0, .5); }
.reason-title { margin: 0 0 8px; font-size: 18px; }
.reason-text { margin: 0 0 12px; color: var(--muted, var(--color-gray-600)); font-size: 14px; }
.reason-label { display: grid; gap: 6px; font-size: 13px; }
.reason-hint { color: var(--muted, var(--color-gray-600)); }
.reason-label textarea { width: 100%; resize: vertical; font: inherit; }
.reason-error { color: var(--danger); font-size: 13px; margin: 8px 0 0; }
.reason-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
</style>
