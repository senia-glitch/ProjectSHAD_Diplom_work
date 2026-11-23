<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="sysstat-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Система</h1>
          <router-link to="/admin" class="btn btn--gry btn--sm">К пользователям</router-link>
        </div>
        <p class="page-desc">Метрики ядра и очередей, обновление раз в 5 секунд</p>
      </div>

      <div v-if="loading" class="loading">Загрузка...</div>
      <template v-else>
        <div v-if="error" class="fmsg fmsg--err">{{ error }}</div>

        <div v-if="stats" class="metrics-grid">
          <div class="metric-card">
            <span class="metric-k">Аптайм</span>
            <span class="metric-v">{{ formatUptime(stats.uptime_seconds) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">Обработано</span>
            <span class="metric-v">{{ stats.total_processed }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">Ошибок</span>
            <span class="metric-v" :class="{ 'metric-v--bad': stats.total_failed }">{{ stats.total_failed }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">В очереди</span>
            <span class="metric-v">{{ stats.total_queued }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">Приём задач</span>
            <span class="metric-v">{{ stats.is_accepting ? 'активен' : 'остановлен' }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">Кэш</span>
            <span class="metric-v">{{ stats.cache_size }}</span>
          </div>
        </div>

        <section v-if="stats" class="card">
          <h2 class="card-title">Каналы</h2>
          <div class="table-wrap">
            <table class="chan-table">
              <thead>
                <tr>
                  <th>Канал</th>
                  <th>Воркеры</th>
                  <th>Очередь</th>
                  <th>Обработано</th>
                  <th>Ошибок</th>
                  <th>Среднее время</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(ch, name) in stats.channels" :key="name">
                  <td class="chan-name">{{ name }}</td>
                  <td>{{ ch.active_workers }} / {{ ch.pool_size }}</td>
                  <td>{{ formatQueueLoad(ch) }}</td>
                  <td>{{ ch.tasks_processed }}</td>
                  <td :class="{ 'metric-v--bad': ch.tasks_failed }">{{ ch.tasks_failed }}</td>
                  <td>{{ formatMs(ch.avg_time_ms) }}</td>
                </tr>
                <tr v-if="!Object.keys(stats.channels || {}).length">
                  <td colspan="6" class="empty-cell">Каналов нет</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <p v-if="serverTime" class="srv-time">
          Серверное время: <span class="srv-time-v">{{ serverTime }}</span>
        </p>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import MainLayout from '../../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../../composables/index.js'
import { formatUptime, formatMs, formatQueueLoad } from '../../../../logic/utils/index.js'
import { useSystemStatsPage } from './useSystemStatsPage.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const { stats, serverTime, loading, error } = useSystemStatsPage()
</script>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
}
.metric-k { font-size: 11px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; color: var(--color-gray-500); }
.metric-v { font-size: 18px; font-weight: 600; color: var(--color-primary); }
.metric-v--bad { color: var(--color-danger); }
.card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  padding: 16px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--color-primary); margin-bottom: 12px; }
.table-wrap { overflow-x: auto; }
.chan-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.chan-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--color-gray-500);
  border-bottom: 2px solid var(--color-gray-200);
}
.chan-table td { padding: 8px 10px; border-bottom: 1px solid var(--color-gray-100); color: var(--color-gray-800); }
.chan-name { font-weight: 600; }
.empty-cell { text-align: center; color: var(--color-gray-500); padding: 20px; }
.srv-time { margin-top: 16px; font-size: 13px; color: var(--color-gray-600); }
.srv-time-v { font-weight: 600; color: var(--color-gray-800); }
</style>
