<template>
  <Teleport to="body">
    <div class="notif-panel" :style="{ top: pos.top + 'px', right: pos.right + 'px' }">
      <div class="notif-head">Уведомления</div>
      <div v-if="loading && !items.length" class="notif-empty">Загрузка…</div>
      <div v-else-if="!items.length" class="notif-empty">Нет уведомлений</div>
      <div v-else class="notif-list">
        <div
          v-for="n in items"
          :key="n.id"
          class="notif-item"
          :class="{ 'notif-item--unread': !n.read }"
          @mouseenter="emit('hover-item', n)"
        >
          <span v-if="!n.read" class="notif-dot"></span>
          <div class="notif-body">
            <div class="notif-text">{{ n.text }}</div>
            <div class="notif-time">{{ formatTime(n.created_at) }}</div>
          </div>
        </div>
      </div>
      <router-link to="/notifications" class="notif-all" @click="emit('close')">Все уведомления</router-link>
    </div>
  </Teleport>
</template>

<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  pos: { type: Object, default: () => ({ top: 0, right: 0 }) },
})
const emit = defineEmits(['hover-item', 'close'])

function formatTime(value) {
  if (!value) return ''
  const d = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.notif-panel {
  position: fixed;
  width: 360px;
  max-width: calc(100vw - 24px);
  background: var(--color-white, #fff);
  border: 1px solid var(--color-gray-300, #d9d9d9);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  z-index: 150;
  overflow: hidden;
}
.notif-head {
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 700;
  border-bottom: 1px solid var(--color-gray-200, #eee);
  color: var(--color-gray-900, #1c1c1c);
}
.notif-empty {
  padding: 14px;
  font-size: 13px;
  color: var(--color-gray-500, #8c8c8c);
}
.notif-list {
  max-height: 420px;
  overflow-y: auto;
}
.notif-item {
  display: flex;
  gap: 10px;
  padding: 10px 14px;
  cursor: default;
  border-bottom: 1px solid var(--color-gray-100, #f5f5f5);
}
.notif-item:last-child { border-bottom: none; }
.notif-item:hover { background: var(--color-gray-50, #fafafa); }
.notif-item--unread { background: rgba(58, 122, 189, 0.04); }
.notif-item--unread:hover { background: rgba(58, 122, 189, 0.08); }
.notif-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-danger);
  margin-top: 6px;
  flex-shrink: 0;
}
.notif-body { min-width: 0; }
.notif-text { font-size: 13px; line-height: 1.35; color: var(--color-gray-900, #1c1c1c); }
.notif-item--unread .notif-text { font-weight: 600; }
.notif-time { font-size: 11px; color: var(--color-gray-500, #8c8c8c); margin-top: 3px; }
.notif-all {
  display: block;
  padding: 9px 14px;
  border-top: 1px solid var(--color-gray-200, #eee);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-accent);
  text-align: center;
}
.notif-all:hover { background: var(--color-gray-50, #fafafa); text-decoration: none; }
</style>
