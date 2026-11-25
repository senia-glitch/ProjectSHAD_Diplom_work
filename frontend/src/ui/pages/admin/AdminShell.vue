<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp admin-shell">
      <div class="admin" :class="{ 'admin--solo': sidebarAllowed }">
        <!-- В информативном виде страницы раздела уже в общем левом меню -->
        <nav v-if="!sidebarAllowed" class="admin-menu" aria-label="Разделы админ-панели">
          <div v-for="group in MENU" :key="group.title" class="admin-group">
            <div class="admin-title">{{ group.title }}</div>
            <router-link
              v-for="item in group.items"
              :key="item.to"
              :to="item.to"
              :class="{ active: isActive(item) }"
              :aria-current="isActive(item) ? 'page' : null"
            >{{ item.label }}</router-link>
          </div>
        </nav>
        <div class="admin-body">
          <div class="toolbar">
            <div>
              <h1>{{ title }}</h1>
              <p v-if="lead" class="lead">{{ lead }}</p>
            </div>
            <div class="row"><slot name="actions" /></div>
          </div>
          <slot />
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
// Оболочка страниц админ-панели владельца: боковое меню разделов + заголовок.
import { useRoute } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useLogout, useNavMode, useUser } from '../../composables/index.js'

defineProps({
  title: { type: String, required: true },
  lead: { type: String, default: '' },
})

const MENU = [
  {
    title: 'Обзор',
    items: [
      { to: '/admin', label: 'Сводка', exact: true },
      { to: '/admin/audit', label: 'Журнал действий' },
    ],
  },
  {
    title: 'Данные',
    items: [
      { to: '/admin/users', label: 'Пользователи' },
      { to: '/admin/db', label: 'База данных' },
    ],
  },
  {
    title: 'Сайт',
    items: [
      { to: '/admin/site', label: 'Гостевая страница' },
      { to: '/blog/manage', label: 'Блог владельца' },
    ],
  },
  {
    title: 'Система',
    items: [
      { to: '/admin/system', label: 'Состояние' },
      { to: '/admin/logs', label: 'Логи' },
      { to: '/admin/key', label: 'Ключ входа' },
    ],
  },
]

const route = useRoute()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const { sidebarAllowed } = useNavMode()

function isActive(item) {
  return item.exact ? route.path === item.to : route.path === item.to || route.path.startsWith(item.to + '/')
}
</script>

<style scoped>
.admin-shell { padding-bottom: 32px; }
.admin--solo { grid-template-columns: minmax(0, 1fr); }
.admin-body :deep(.toolbar .row:empty) { display: none; }
</style>
