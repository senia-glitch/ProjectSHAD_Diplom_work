<template>
  <AdminShell title="Ключ входа" lead="Вход в админ-панель возможен только по ключу. В базе хранится лишь его хэш.">
    <section class="panel stack-sm">
      <h3>Выпустить новый ключ</h3>
      <p class="muted">Старый ключ перестанет действовать сразу. Новый ключ будет показан один раз — сохраните его в менеджере паролей.
        Текущая сессия продолжит работать.</p>
      <div>
        <button type="button" class="btn danger" :disabled="loading" @click="rotate">{{ loading ? 'Выпуск…' : 'Выпустить новый ключ' }}</button>
      </div>
      <div v-if="error" class="notice error" role="alert">{{ error }}</div>
      <div v-if="newKey" class="notice ok stack-sm">
        <strong>Новый ключ (больше не будет показан):</strong>
        <div class="row key-row">
          <code class="mono key-value">{{ newKey }}</code>
          <button type="button" class="btn ghost" @click="copy">{{ copied ? 'Скопировано' : 'Копировать' }}</button>
        </div>
      </div>
    </section>
    <section class="panel stack-sm">
      <h3>Если ключ потерян</h3>
      <p class="muted">На сервере выполните команду — она выпустит новый ключ и покажет его в терминале:</p>
      <pre class="mono cmd">./deploy/deploy.sh admin-key &lt;логин&gt;</pre>
    </section>
  </AdminShell>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AdminShell from './AdminShell.vue'
import { rotateAdminKey } from '../../../logic/actions/index.js'
import { askConfirm } from '../../legacy/testing/kit.js'

const loading = ref(false)
const error = ref('')
const newKey = ref('')
const copied = ref(false)

async function rotate() {
  const ok = await askConfirm('Выпустить новый ключ?', 'Текущий ключ перестанет действовать. Новый будет показан только один раз.', { okText: 'Выпустить', danger: true })
  if (!ok) return
  loading.value = true
  error.value = ''
  copied.value = false
  try {
    newKey.value = (await rotateAdminKey()).key
  } catch (e) {
    error.value = e.message || 'Не удалось выпустить ключ'
  } finally {
    loading.value = false
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(newKey.value)
    copied.value = true
  } catch {
    copied.value = false
  }
}

onMounted(() => { document.title = 'Ключ входа · SHAD' })
// Ключ не держим в памяти дольше, чем открыта страница.
onBeforeUnmount(() => { newKey.value = '' })
</script>

<style scoped>
.panel { margin-bottom: 16px; }
.panel h3 { margin: 0; font-size: 15px; }
.key-row { gap: 12px; align-items: center; flex-wrap: wrap; }
.key-value { padding: 8px 10px; border-radius: 8px; background: var(--surface-2); word-break: break-all; user-select: all; }
.cmd { margin: 0; padding: 10px 12px; border-radius: 8px; background: var(--surface-2); overflow-x: auto; }
</style>
