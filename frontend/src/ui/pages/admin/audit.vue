<template>
  <AdminShell title="Журнал действий" lead="Входы по ключу, действия с пользователями и все операции с базой данных.">
    <div class="row filters">
      <select v-model="action" aria-label="Тип действия" @change="load(0)">
        <option value="">Все действия</option>
        <option v-for="(label, key) in ACTION_LABELS" :key="key" :value="key">{{ label }}</option>
      </select>
      <span class="muted small">{{ total ? `${offset + 1}–${offset + items.length} из ${total}` : '' }}</span>
    </div>
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-else-if="loading && !items.length" class="skeleton" aria-hidden="true"></div>
    <p v-else-if="!items.length" class="muted">Записей нет.</p>
    <AuditTable v-else :items="items" />
    <div v-if="total > PAGE" class="pager">
      <button type="button" class="btn ghost" :disabled="offset === 0 || loading" @click="load(Math.max(0, offset - PAGE))">← Новее</button>
      <button type="button" class="btn ghost" :disabled="offset + PAGE >= total || loading" @click="load(offset + PAGE)">Старее →</button>
    </div>
  </AdminShell>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import AdminShell from './AdminShell.vue'
import AuditTable from './AuditTable.vue'
import { loadAdminAudit } from '../../../logic/actions/index.js'
import { ACTION_LABELS } from './adminFormat.js'

const PAGE = 100
const action = ref('')
const items = ref([])
const total = ref(0)
const offset = ref(0)
const loading = ref(false)
const error = ref('')

async function load(nextOffset = 0) {
  loading.value = true
  error.value = ''
  try {
    const data = await loadAdminAudit({ action: action.value || undefined, limit: PAGE, offset: nextOffset })
    items.value = data.items
    total.value = data.total
    offset.value = nextOffset
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить журнал'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  document.title = 'Журнал действий · SHAD'
  load(0)
})
</script>

<style scoped>
.filters { gap: 12px; align-items: center; margin-bottom: 12px; }
.filters select { width: auto; min-width: 220px; }
</style>
