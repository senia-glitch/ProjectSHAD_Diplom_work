<template>
  <div class="table-wrap audit-table">
    <table>
      <thead><tr><th>Когда</th><th>Действие</th><th>Объект</th><th v-if="!compact">Подробности</th><th>Адрес</th></tr></thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td class="nowrap">{{ when(item.created_at) }}</td>
          <td><span class="badge" :class="tone(item.action)">{{ label(item.action) }}</span></td>
          <td class="mono small">{{ item.target || '—' }}</td>
          <td v-if="!compact" class="details mono small">{{ details(item.details) }}</td>
          <td class="mono small muted">{{ item.ip || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
// Таблица журнала действий администратора (сводка и страница журнала).
import { ACTION_LABELS, formatLocalDateTime } from './adminFormat.js'

defineProps({
  items: { type: Array, required: true },
  compact: { type: Boolean, default: false },
})

const label = (action) => ACTION_LABELS[action] || action
const tone = (action) => (action === 'login_failed' || action.includes('delete') || action === 'block_user' ? 'fail' : action.startsWith('db_') ? 'sched' : 'ok')
const when = (iso) => formatLocalDateTime(iso)
function details(value) {
  if (!value || (typeof value === 'object' && !Object.keys(value).length)) return '—'
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  return text.length > 240 ? text.slice(0, 240) + '…' : text
}
</script>

<style scoped>
.details { max-width: 420px; word-break: break-word; white-space: pre-wrap; }
</style>
