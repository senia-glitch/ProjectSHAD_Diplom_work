<template>
  <div class="layout">
    <a class="skip-link" href="#main-content">Перейти к содержимому</a>
    <header class="header">
      <nav class="nav" aria-label="Основная навигация">
        <router-link to="/" class="nav-logo" aria-label="SHAD — главная">
          <span class="brand-mark" aria-hidden="true">S</span>
          <span class="brand-name">SHAD<span class="brand-caption">пространство для занятий</span></span>
        </router-link>
        <div ref="navLinks" class="nav-links" :class="{ 'nav-links--public': !isLoggedIn }">
          <template v-if="!isLoggedIn">
            <router-link to="/how-it-works" class="nav-link"><span class="nav-lbl">Как это работает</span></router-link>
            <router-link to="/for-tutors" class="nav-link"><span class="nav-lbl">Репетиторам</span></router-link>
            <router-link to="/faq" class="nav-link"><span class="nav-lbl">Вопросы</span></router-link>
          </template>
          <router-link v-if="isLoggedIn" to="/profile" class="nav-link"><span class="nav-ico nav-ico--profile" aria-hidden="true"></span><span class="nav-lbl">Профиль</span></router-link>
          <router-link v-if="isLoggedIn && role === 'student'" to="/tutors" class="nav-link"><span class="nav-ico nav-ico--tutors" aria-hidden="true"></span><span class="nav-lbl">Репетиторы</span></router-link>
          <router-link v-if="isLoggedIn && role === 'student'" to="/student-settings" class="nav-link"><span class="nav-ico nav-ico--settings" aria-hidden="true"></span><span class="nav-lbl">Настройки</span></router-link>
          <router-link v-if="isLoggedIn && role === 'tutor'" to="/students" class="nav-link"><span class="nav-ico nav-ico--students" aria-hidden="true"></span><span class="nav-lbl">Ученики</span></router-link>
          <router-link v-if="isLoggedIn && role === 'tutor'" to="/settings" class="nav-link"><span class="nav-ico nav-ico--settings" aria-hidden="true"></span><span class="nav-lbl">Настройки</span></router-link>
          <router-link v-if="isLoggedIn && role === 'tutor'" to="/bookings" class="nav-link"><span class="nav-ico nav-ico--bookings" aria-hidden="true"></span><span class="nav-lbl">Брони</span></router-link>
          <router-link v-if="isLoggedIn && role === 'tutor'" to="/statistics" class="nav-link"><span class="nav-ico nav-ico--statistics" aria-hidden="true"></span><span class="nav-lbl">Статистика</span></router-link>
          <router-link v-if="isLoggedIn" to="/schedule" class="nav-link"><span class="nav-ico nav-ico--schedule" aria-hidden="true"></span><span class="nav-lbl">Расписание</span></router-link>
          <router-link v-if="isLoggedIn && role === 'admin'" to="/admin" class="nav-link"><span class="nav-ico nav-ico--admin" aria-hidden="true"></span><span class="nav-lbl">Управление</span></router-link>
        </div>
        <div class="nav-auth">
          <button type="button" class="theme-toggle" :aria-label="theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'" :title="theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'" :aria-pressed="theme === 'light'" @click="toggleTheme">
            <UiIcon :name="theme === 'dark' ? 'sun' : 'moon'" />
          </button>
          <template v-if="isLoggedIn">
            <div class="notif-area">
              <button ref="bellRef" class="nav-link nav-link--btn notif-bell" aria-label="Уведомления" title="Уведомления" :aria-expanded="panelOpen" @click="handleBellClick">
                <span class="nav-ico nav-ico--bell" aria-hidden="true"></span>
                <span class="nav-lbl">Уведомления</span>
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
            <button class="nav-link nav-link--btn" aria-label="Выйти" title="Выйти" @click="emit('logout')"><span class="nav-ico nav-ico--logout" aria-hidden="true"></span><span class="nav-lbl">Выйти</span></button>
          </template>
          <template v-else>
            <router-link to="/login" class="nav-link"><span class="nav-ico nav-ico--login" aria-hidden="true"></span><span class="nav-lbl">Войти</span></router-link>
            <router-link to="/register" class="nav-link"><span class="nav-ico nav-ico--register" aria-hidden="true"></span><span class="nav-lbl">Регистрация</span></router-link>
          </template>
        </div>
      </nav>
    </header>
    <main id="main-content" class="main" tabindex="-1">
      <slot />
    </main>
    <footer class="footer"><span>SHAD Tutoring</span><span>Меньше рутины. Больше времени на занятия.</span></footer>
  </div>
</template>

<script setup>
// Оболочка страниц. Данных и вызовов не имеет: состояние — пропсами,
// действия — эмитами от страницы (§10: blocks без logic).
import { ref, onMounted } from 'vue'
import NotificationPanel from './NotificationPanel.vue'
import { UiIcon } from '../../components/index.js'
import { useNotifications, useTheme } from '../../composables/index.js'

defineProps({
  isLoggedIn: { type: Boolean, default: false },
  role: { type: String, default: '' },
})
const emit = defineEmits(['logout'])
const { theme, toggleTheme } = useTheme()
const navLinks = ref(null)
onMounted(() => {
  const active = navLinks.value?.querySelector('.router-link-active')
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
.header { position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter: blur(12px); }
.nav { display: flex; align-items: center; gap: 24px; min-height: var(--header-h); max-width: 1208px; margin: 0 auto; padding: 0 24px; }
.nav-logo { display: flex; align-items: center; gap: 10px; color: var(--text); flex-shrink: 0; text-decoration: none; }
.nav-logo:hover { text-decoration: none; }
.brand-mark { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 10px; background: var(--accent); color: var(--on-accent); font-size: 20px; font-weight: 700; }
.brand-name { font-size: 16px; font-weight: 700; letter-spacing: .04em; line-height: 1.25; }
.brand-caption { display: block; font-size: 10px; font-weight: 400; color: var(--muted); letter-spacing: 0; margin-top: 3px; }
.nav-links { display: flex; gap: 4px; align-self: stretch; align-items: center; margin: 0 auto; min-width: 0; }
.nav-link { position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 9px 10px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); font: inherit; font-size: 12px; font-weight: 500; text-decoration: none; cursor: pointer; white-space: nowrap; transition: background var(--t), color var(--t); }
.nav-link:hover { background: var(--surface-2); color: var(--text); text-decoration: none; }
.nav-link.router-link-active { color: var(--accent); background: var(--accent-soft); }
.nav-links .nav-link.router-link-active::after { content: ''; position: absolute; bottom: -13px; height: 2px; background: var(--accent); left: 10px; right: 10px; }
.nav-link .nav-ico { width: 18px; height: 18px; }
.nav-auth { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.nav-auth .nav-lbl { display: none; }
.nav-auth > a:last-child { background: var(--accent); color: var(--on-accent); }
.nav-auth > a .nav-lbl { display: inline; }
.nav-auth > a .nav-ico { display: none; }
.theme-toggle { display: grid; place-items: center; width: 36px; height: 36px; background: transparent; color: var(--muted); border: 1px solid var(--line); border-radius: 10px; cursor: pointer; margin-right: 4px; }
.theme-toggle:hover { background: var(--surface-2); color: var(--text); border-color: var(--line-strong); }
.notif-area, .notif-bell { position: relative; }
.notif-badge { position: absolute; top: 0; right: 0; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: var(--danger); color: var(--on-accent); font-size: 10px; font-weight: 700; line-height: 16px; text-align: center; }
.main { flex: 1; padding: 32px 24px 40px; max-width: 1208px; margin: 0 auto; width: 100%; min-width: 0; }
.main:focus { outline: none; }
.footer { display: flex; justify-content: space-between; gap: 16px; width: calc(100% - 48px); max-width: 1160px; margin: 0 auto; padding: 16px 0 24px; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; }
@media (max-width: 1150px) {
  .brand-caption { display: none; }
  .nav { gap: 16px; }
  .nav-link { padding-inline: 8px; }
}
@media (max-width: 950px) {
  .nav { display: grid; grid-template-columns: 1fr auto; gap: 0 16px; padding-top: 12px; }
  .nav-logo { grid-column: 1; grid-row: 1; }
  .nav-auth { grid-column: 2; grid-row: 1; }
  .nav-links { grid-column: 1 / -1; grid-row: 2; margin: 8px 0 0; overflow-x: auto; padding: 4px 0 10px; scrollbar-width: thin; }
  .nav-links .nav-link.router-link-active::after { bottom: -10px; }
  .nav-link { padding: 8px 12px; }
}
@media (max-width: 600px) {
  .nav { padding-inline: 16px; }
  .main { padding: 24px 16px 32px; }
  .nav-links { gap: 0; }
  .nav-links .nav-link { flex-direction: column; gap: 4px; font-size: 11px; padding: 8px 12px; }
  .nav-links--public .nav-link { flex-direction: row; padding: 8px; }
  .nav-auth .nav-link { padding: 8px; }
  .footer { width: calc(100% - 32px); flex-direction: column; gap: 4px; }
}
</style>
