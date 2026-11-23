<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="notif-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Уведомления</h1>
          <button
            v-if="unreadCount > 0"
            type="button"
            class="btn btn--gry btn--sm"
            :disabled="markingAll"
            @click="handleMarkAll"
          >
            {{ markingAll ? '...' : 'Прочитать все' }}
          </button>
        </div>
        <p class="page-desc">События по записям, урокам и оплатам</p>
      </div>

      <div class="notif-tabs">
        <button
          type="button"
          class="tab"
          :class="{ active: filter === 'all' }"
          @click="filter = 'all'"
        >
          Все
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: filter === 'unread' }"
          @click="filter = 'unread'"
        >
          Непрочитанные<span v-if="unreadCount" class="tab-count">{{ unreadCount }}</span>
        </button>
      </div>

      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="loadErr" class="fmsg fmsg--err">{{ loadErr }}</div>
      <div v-else-if="!groups.length" class="empty">
        {{ filter === 'unread' ? 'Непрочитанных уведомлений нет' : 'Уведомлений пока нет' }}
      </div>

      <template v-else>
        <section v-for="group in groups" :key="group.key" class="notif-group">
          <h2 class="notif-day">{{ group.label }}</h2>
          <div class="notif-card">
            <div
              v-for="n in group.items"
              :key="n.id"
              class="notif-row"
              :class="{ 'notif-row--unread': !n.read }"
              @click="handleRead(n)"
            >
              <span v-if="!n.read" class="notif-row-dot" />
              <div class="notif-row-body">
                <div class="notif-row-text">{{ n.text }}</div>
                <div class="notif-row-time">{{ formatNotifTime(n.created_at) }}</div>
              </div>
            </div>
          </div>
        </section>

        <div v-if="hasMore" class="more-row">
          <button type="button" class="btn btn--gry" :disabled="loadingMore" @click="handleMore">
            {{ loadingMore ? '...' : 'Показать ещё' }}
          </button>
        </div>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { loadNotifications, loadMoreNotifications, markRead, markAllRead } from '../../../logic/actions/index.js'
import { useNotificationsStore } from '../../../logic/store/index.js'
import { groupNotificationsByDay, formatNotifTime } from '../../../logic/utils/index.js'
import { logError } from '../../../logic/logger/index.js'

const PAGE_SIZE = 50

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()

const store = useNotificationsStore()
const filter = ref('all')
const loading = ref(true)
const loadingMore = ref(false)
const markingAll = ref(false)
const loadErr = ref('')
const hasMore = ref(false)

const unreadCount = computed(() => store.unreadCount)
const groups = computed(() => {
  const items = filter.value === 'unread' ? store.items.filter((n) => !n.read) : store.items
  return groupNotificationsByDay(items)
})

async function load() {
  loading.value = true
  loadErr.value = ''
  try {
    const data = await loadNotifications({ limit: PAGE_SIZE })
    hasMore.value = (data.notifications || []).length === PAGE_SIZE
  } catch (e) {
    loadErr.value = e.message || 'Не удалось загрузить уведомления'
    logError('notifications', 'load:error', { error: e.message })
  } finally {
    loading.value = false
  }
}

async function handleRead(n) {
  if (n.read) return
  try {
    await markRead(n.id)
  } catch (e) {
    logError('notifications', 'read:error', { error: e.message })
  }
}

async function handleMarkAll() {
  markingAll.value = true
  try {
    await markAllRead()
  } catch (e) {
    logError('notifications', 'read-all:error', { error: e.message })
  } finally {
    markingAll.value = false
  }
}

async function handleMore() {
  loadingMore.value = true
  try {
    const data = await loadMoreNotifications({ limit: PAGE_SIZE })
    hasMore.value = (data.notifications || []).length === PAGE_SIZE
  } catch (e) {
    logError('notifications', 'more:error', { error: e.message })
  } finally {
    loadingMore.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.notif-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}
.tab {
  padding: 6px 12px;
  border: none;
  background: none;
  border-radius: var(--radius-md, 6px);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-gray-600);
  cursor: pointer;
}
.tab:hover { background: var(--color-gray-100); }
.tab.active { background: var(--color-white); color: var(--color-primary); box-shadow: var(--shadow-sm); }
.tab-count {
  display: inline-block;
  min-width: 16px;
  margin-left: 6px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--color-danger);
  color: var(--color-white);
  font-size: 11px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
.notif-group { margin-bottom: 20px; }
.notif-day {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-gray-600);
  margin-bottom: 8px;
}
.notif-card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
}
.notif-row {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--color-gray-100);
}
.notif-row:last-child { border-bottom: none; }
.notif-row:hover { background: var(--color-gray-50); }
.notif-row--unread { background: rgba(58, 122, 189, 0.04); }
.notif-row--unread:hover { background: rgba(58, 122, 189, 0.08); }
.notif-row-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  margin-top: 6px;
  flex-shrink: 0;
}
.notif-row-body { min-width: 0; }
.notif-row-text { font-size: 14px; line-height: 1.4; color: var(--color-gray-800); }
.notif-row--unread .notif-row-text { font-weight: 600; }
.notif-row-time { font-size: 11px; color: var(--color-gray-500); margin-top: 3px; }
.empty {
  padding: 40px 20px;
  text-align: center;
  font-size: 14px;
  color: var(--color-gray-500);
}
.more-row { display: flex; justify-content: center; margin-top: 16px; }
</style>
