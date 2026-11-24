<template>
  <div class="layout">
    <a class="skip-link" href="#main-content">Перейти к содержимому</a>
    <div class="pp shell-top">
      <header class="site-header">
        <div class="wrap header-inner">
          <router-link to="/" class="brand" aria-label="SHAD — на главную">
            <svg class="brand-logo" viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
              <rect width="32" height="32" rx="8" fill="currentColor" />
              <path d="M21 10.5c-1-1.3-2.6-2-4.6-2-2.9 0-4.9 1.5-4.9 3.7 0 4.9 9.9 2.6 9.9 7.6 0 2.3-2.1 3.8-5.1 3.8-2.2 0-4-.8-5.1-2.3" fill="none" stroke="var(--accent-ink)" stroke-width="2.4" stroke-linecap="round" />
            </svg>
            <span class="brand-name">SHAD</span>
          </router-link>
          <nav ref="navLinks" class="nav-main" aria-label="Разделы">
            <router-link
              v-for="item in navItems"
              :key="item.to"
              v-slot="{ href, navigate, isActive }"
              :to="item.to"
              custom
            >
              <a :href="href" :data-tip="item.label" :aria-current="isActive || isSection(item) ? 'page' : null" @click="navigate">
                <span class="icon" :data-icon="item.icon"><UiIcon :name="item.icon" /></span>
                <span class="nav-label">{{ item.label }}</span>
              </a>
            </router-link>
          </nav>
          <div class="header-actions">
            <div v-if="isLoggedIn" class="notif-area">
              <button ref="bellRef" type="button" class="btn icon notif-bell" aria-label="Уведомления" data-tip="Уведомления" :aria-expanded="panelOpen" @click="handleBellClick">
                <span class="icon" data-icon="bell"><UiIcon name="bell" /></span>
                <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount }}</span>
              </button>
              <NotificationPanel
                v-if="panelOpen"
                :items="items"
                :loading="notifLoading"
                :pos="panelPos"
                @hover-item="onHoverItem"
                @close="closePanel"
              />
            </div>
            <button type="button" class="btn icon" :aria-label="theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'" :data-tip="theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'" :aria-pressed="theme === 'light'" @click="toggleTheme">
              <span class="icon" :data-icon="theme === 'dark' ? 'sun' : 'moon'"><UiIcon :name="theme === 'dark' ? 'sun' : 'moon'" /></span>
            </button>
            <button v-if="isLoggedIn" type="button" class="btn icon" aria-label="Выйти" data-tip="Выйти" @click="emit('logout')">
              <span class="icon" data-icon="logout"><UiIcon name="logout" /></span>
            </button>
            <template v-else>
              <router-link to="/login" class="btn ghost">Войти</router-link>
              <router-link to="/register" class="btn primary nav-register">Регистрация</router-link>
            </template>
          </div>
        </div>
      </header>
    </div>
    <main id="main-content" class="main" tabindex="-1">
      <slot />
    </main>
    <div class="pp">
      <footer class="site-footer">
        <div class="wrap footer-inner">
          <span>© SHAD — расписание, тесты, доски и блог репетиторов</span>
          <nav class="footer-nav" aria-label="Ссылки">
            <router-link to="/blog">Блог</router-link>
            <router-link to="/how-it-works">Как это работает</router-link>
            <router-link to="/faq">Вопросы</router-link>
          </nav>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
// Оболочка страниц. Данных и вызовов не имеет: состояние — пропсами,
// действия — эмитами от страницы (§10: blocks без logic).
// Шапка и подвал оформлены по эталону ProjectProgon (My_Blog): классы из styles/pp.css внутри .pp.
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import NotificationPanel from './NotificationPanel.vue'
import { UiIcon } from '../../components/index.js'
import { useNotifications, useTheme } from '../../composables/index.js'

const props = defineProps({
  isLoggedIn: { type: Boolean, default: false },
  role: { type: String, default: '' },
})
const emit = defineEmits(['logout'])
const route = useRoute()
const { theme, toggleTheme } = useTheme()

const NAV = {
  guest: [
    { to: '/how-it-works', label: 'Как это работает', icon: 'info' },
    { to: '/for-tutors', label: 'Репетиторам', icon: 'users' },
    { to: '/blog', label: 'Блог', icon: 'blog' },
    { to: '/faq', label: 'Вопросы', icon: 'chat' },
  ],
  student: [
    { to: '/schedule', label: 'Расписание', icon: 'calendar' },
    { to: '/tutors', label: 'Репетиторы', icon: 'users' },
    { to: '/testing', label: 'Тесты', icon: 'tests' },
    { to: '/boards', label: 'Доски', icon: 'board' },
    { to: '/blog', label: 'Блог', icon: 'blog' },
    { to: '/profile', label: 'Профиль', icon: 'user' },
    { to: '/student-settings', label: 'Настройки', icon: 'sliders' },
  ],
  tutor: [
    { to: '/schedule', label: 'Расписание', icon: 'calendar' },
    { to: '/students', label: 'Ученики', icon: 'users' },
    { to: '/bookings', label: 'Брони', icon: 'clock' },
    { to: '/statistics', label: 'Статистика', icon: 'chart' },
    { to: '/testing', label: 'Тесты', icon: 'tests' },
    { to: '/boards', label: 'Доски', icon: 'board' },
    { to: '/blog/manage', label: 'Блог', icon: 'blog', section: '/blog' },
    { to: '/profile', label: 'Профиль', icon: 'user' },
    { to: '/settings', label: 'Настройки', icon: 'sliders' },
  ],
  admin: [
    { to: '/admin', label: 'Управление', icon: 'shield' },
    { to: '/blog', label: 'Блог', icon: 'blog' },
    { to: '/profile', label: 'Профиль', icon: 'user' },
  ],
}
const navItems = computed(() => (props.isLoggedIn ? NAV[props.role] || [] : NAV.guest))
// Раздел подсвечивается и на вложенных страницах (тест, доска, запись блога).
function isSection(item) {
  const base = item.section || item.to
  return route.path === base || route.path.startsWith(base + '/')
}

const navLinks = ref(null)
onMounted(() => {
  const active = navLinks.value?.querySelector('[aria-current="page"]')
  if (active) navLinks.value.scrollLeft = Math.max(0, active.offsetLeft - navLinks.value.offsetLeft - 16)
})

const { items, unreadCount, panelOpen, loading: notifLoading, openPanel, closePanel, onHoverItem } = useNotifications()
const bellRef = ref(null)
const panelPos = ref({ top: 0, right: 0 })

function handleBellClick() {
  if (!panelOpen.value && bellRef.value) {
    const r = bellRef.value.getBoundingClientRect()
    const width = document.documentElement.clientWidth
    const panelWidth = Math.min(360, width - 24)
    const right = Math.min(Math.max(12, width - r.right), width - panelWidth - 12)
    panelPos.value = { top: r.bottom + 6, right }
  }
  openPanel()
}
</script>

<style scoped>
.layout { display: flex; flex-direction: column; min-height: 100dvh; }
.shell-top { position: sticky; top: 0; z-index: 100; }
.pp .site-header { position: static; }
.pp .brand-name { letter-spacing: .04em; }
.notif-area { position: relative; }
.notif-badge { position: absolute; top: 1px; right: 1px; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: var(--danger); color: var(--accent-ink); font-size: 10px; font-weight: 700; line-height: 16px; text-align: center; }
.pp .header-actions .btn.icon { width: var(--ctl); padding: 0; border: 1px solid var(--line); }
.main { flex: 1; padding: 40px 24px 80px; max-width: 1208px; margin: 0 auto; width: 100%; min-width: 0; }
.main:focus { outline: none; }
@media (max-width: 720px) {
  .shell-top { position: static; }
  .main { padding: 28px 16px 56px; }
  .nav-register { display: none !important; }
}
</style>
