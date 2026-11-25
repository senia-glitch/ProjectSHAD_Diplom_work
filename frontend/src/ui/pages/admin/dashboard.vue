<template>
  <AdminShell title="Сводка" lead="Состояние платформы и последние действия администратора.">
    <template #actions>
      <button type="button" class="btn ghost" :disabled="loading" @click="load">Обновить</button>
    </template>
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-else-if="loading && !data" class="sk-stack" aria-hidden="true"><div class="skeleton"></div><div class="skeleton"></div></div>
    <template v-else-if="data">
      <div class="tiles">
        <router-link v-for="tile in tiles" :key="tile.label" :to="tile.to" class="tile">
          <span class="tile-value">{{ tile.value }}</span>
          <span class="tile-label">{{ tile.label }}</span>
          <span v-if="tile.note" class="tile-note">{{ tile.note }}</span>
        </router-link>
      </div>

      <div class="two">
        <section class="panel">
          <h3>Уроки за 30 дней</h3>
          <p v-if="!statuses.length" class="muted">Уроков не было.</p>
          <div v-for="s in statuses" :key="s.key" class="kv"><span>{{ s.label }}</span><strong>{{ s.value }}</strong></div>
        </section>
        <section class="panel">
          <h3>Контент</h3>
          <div class="kv"><span>Записи блогов</span><strong>{{ data.blog_posts }}</strong></div>
          <div class="kv"><span>Доски</span><strong>{{ data.boards }}</strong></div>
          <div class="kv"><span>Тесты</span><strong>{{ data.quizzes }}</strong></div>
          <div class="kv"><span>Новых пользователей за 30 дней</span><strong>{{ data.new_users_30d }}</strong></div>
        </section>
      </div>

      <section class="panel">
        <div class="kv"><h3>Последние действия</h3><router-link to="/admin/audit" class="more">Весь журнал →</router-link></div>
        <p v-if="!data.recent_audit.length" class="muted">Записей пока нет.</p>
        <AuditTable v-else :items="data.recent_audit" compact />
      </section>
    </template>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AdminShell from './AdminShell.vue'
import AuditTable from './AuditTable.vue'
import { loadAdminDashboard } from '../../../logic/actions/index.js'

const STATUS = {
  SCHEDULED: 'Запланированы', PENDING: 'Ждут подтверждения', ONGOING: 'Идут', FINISHED: 'Проведены',
  CANCELLED: 'Отменены', NO_SHOW: 'Неявка', REJECTED: 'Отклонены', SYSTEM_FINISHED: 'Завершены системой',
}

const data = ref(null)
const loading = ref(false)
const error = ref('')

const tiles = computed(() => {
  const d = data.value
  const r = d.users_by_role || {}
  return [
    { label: 'Ученики', value: r.student || 0, to: '/admin/users', note: `+${d.new_users_7d} за неделю (все роли)` },
    { label: 'Репетиторы', value: r.tutor || 0, to: '/admin/users' },
    { label: 'Заблокированы', value: d.blocked_users, to: '/admin/users' },
    { label: 'Уроков на 7 дней', value: d.lessons_next_7d, to: '/admin/db' },
    { label: 'Заявки ждут ответа', value: d.pending_requests, to: '/admin/db' },
  ]
})
const statuses = computed(() => Object.entries(data.value?.lessons_by_status_30d || {})
  .map(([key, value]) => ({ key, value, label: STATUS[key] || key }))
  .sort((a, b) => b.value - a.value))

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await loadAdminDashboard()
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить сводку'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  document.title = 'Админ-панель · SHAD'
  load()
})
</script>

<style scoped>
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; margin-bottom: 16px; }
.tile { display: grid; gap: 4px; padding: 16px 18px; border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--surface); color: var(--text); transition: border-color var(--t); }
.tile:hover { border-color: var(--accent); text-decoration: none; }
.tile-value { font-size: 28px; font-weight: 600; letter-spacing: -.02em; }
.tile-label { font-size: 13px; color: var(--muted); }
.tile-note { font-size: 12px; color: var(--accent); }
.two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }
.panel { display: grid; gap: 10px; align-content: start; }
.panel h3 { margin: 0; font-size: 15px; }
@media (max-width: 800px) { .two { grid-template-columns: minmax(0, 1fr); } }
</style>
