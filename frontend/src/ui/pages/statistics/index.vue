<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="page-header">
      <div class="page-title-row">
        <h1 class="page-title">Статистика</h1>
        <span class="page-period">{{ periodCaption }}</span>
      </div>
      <p class="page-desc">Выручка, нагрузка и прогноз практики</p>
    </div>

    <nav class="tabs">
      <router-link to="/statistics/overview" class="tab-link">Динамика</router-link>
      <router-link to="/statistics/lessons" class="tab-link">Уроки</router-link>
      <router-link to="/statistics/students" class="tab-link">Ученики</router-link>
      <router-link to="/statistics/payments" class="tab-link">Оплаты</router-link>
    </nav>

    <div class="dash">
      <div class="dash-main">
        <router-view />
      </div>
      <FiltersPanel :years="years" :students="students" :tab="tab" :top="barTop" />
    </div>

  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import FiltersPanel from './FiltersPanel.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { useStatisticsPage } from './useStatisticsPage.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const { filters, years, students, dateRange } = useStatisticsPage({ root: true })

const barTop = ref(84)
const route = useRoute()

// Сайдбар показывает настройки открытого блока.
const tab = computed(() => {
  if (route.name === 'statistics-lessons') return 'lessons'
  if (route.name === 'statistics-students') return 'students'
  if (route.name === 'statistics-payments') return 'payments'
  return 'dynamics'
})

onMounted(() => {
  const header = document.querySelector('.header')
  if (header) barTop.value = header.offsetHeight + 12
})

const MONTHS_FULL = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']

const periodCaption = computed(() => {
  if (tab.value === 'dynamics') {
    return filters.dynMode === 'week' ? `${filters.year} год · недели` : `${filters.year} год`
  }
  if (filters.preset === 'month' && /^\d{4}-\d{2}$/.test(filters.month)) {
    const [y, m] = filters.month.split('-').map(Number)
    return `${MONTHS_FULL[m - 1]} ${y}`
  }
  if (filters.preset === 'year') return `${filters.year} год`
  const [a, b] = dateRange.value
  const fmt = (iso) => `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}`
  return a === b ? fmt(a) : `${fmt(a)} – ${fmt(b)}`
})
</script>

<style scoped>
.page-period { margin-left: auto; font-size: 14px; color: var(--color-gray-600); }
.tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.tab-link {
  padding: 8px 18px; border-radius: 8px; font-size: 14px; font-weight: 500;
  color: var(--color-gray-600); text-decoration: none;
}
.tab-link:hover { background: var(--color-gray-100); text-decoration: none; }
.tab-link.router-link-exact-active { background: var(--color-white); color: var(--color-gray-800); box-shadow: var(--shadow-sm); }
.dash { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 16px; align-items: start; }
.dash-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
@media (max-width: 1000px) {
  .dash { grid-template-columns: 1fr; }
}
</style>
