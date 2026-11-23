<template>
  <div class="layout">
    <header class="header">
      <nav class="nav">
        <router-link to="/" class="nav-logo">SHAD</router-link>
        <div class="nav-links">
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
          <template v-if="isLoggedIn">
            <div class="notif-area">
              <button ref="bellRef" class="nav-link nav-link--btn notif-bell" @click="handleBellClick">
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
            <button class="nav-link nav-link--btn" @click="emit('logout')"><span class="nav-ico nav-ico--logout" aria-hidden="true"></span><span class="nav-lbl">Выйти</span></button>
          </template>
          <template v-else>
            <router-link to="/login" class="nav-link"><span class="nav-ico nav-ico--login" aria-hidden="true"></span><span class="nav-lbl">Войти</span></router-link>
            <router-link to="/register" class="nav-link"><span class="nav-ico nav-ico--register" aria-hidden="true"></span><span class="nav-lbl">Регистрация</span></router-link>
          </template>
        </div>
      </nav>
    </header>
    <main class="main">
      <slot />
    </main>
  </div>
</template>

<script setup>
// Оболочка страниц. Данных и вызовов не имеет: состояние — пропсами,
// действия — эмитами от страницы (§10: blocks без logic).
import { ref } from 'vue'
import NotificationPanel from './NotificationPanel.vue'
import { useNotifications } from '../../composables/index.js'

defineProps({
  isLoggedIn: { type: Boolean, default: false },
  role: { type: String, default: '' },
})
const emit = defineEmits(['logout'])

const { items, unreadCount, panelOpen, loading: notifLoading, openPanel, closePanel, onHoverItem } = useNotifications()
const bellRef = ref(null)
const panelPos = ref({ top: 0, right: 0 })

function handleBellClick() {
  if (!panelOpen.value && bellRef.value) {
    const r = bellRef.value.getBoundingClientRect()
    panelPos.value = { top: r.bottom + 6, right: window.innerWidth - r.right }
  }
  openPanel()
}
</script>

<style scoped>
.layout { display: flex; flex-direction: column; min-height: 100vh; }
.header { background-color: var(--color-primary); box-shadow: var(--shadow-md); position: sticky; top: 0; z-index: 100; }
.nav { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 8px; padding: 8px 16px; width: 100%; overflow-x: auto; }
.nav-logo { font-size: 18px; font-weight: 700; color: white; text-decoration: none; padding: 8px 12px; white-space: nowrap; justify-self: start; }
.nav-logo:hover { text-decoration: none; }
.nav-links { display: flex; align-items: center; gap: 4px; justify-self: center; }
.nav-auth { display: flex; align-items: center; gap: 4px; justify-self: end; }
.nav-link {
  display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 10px; border-radius: 6px;
  color: white; font-size: 14px; font-weight: 500; text-decoration: none; white-space: nowrap;
  transition: background 150ms; border: none; background: none; cursor: pointer;
}
.nav-link:hover { background: rgba(255,255,255,0.1); text-decoration: none; }
.nav-link:hover .nav-ico { transform: scale(1.12); }
.nav-link.router-link-exact-active { background: rgba(255,255,255,0.2); }
.nav-link.router-link-exact-active .nav-ico { transform: scale(1.12); }
.nav-link.router-link-exact-active .nav-lbl { color: var(--color-accent-100); }
.nav-lbl { font-size: 10px; font-weight: 500; line-height: 1.2; }
.nav-link--btn { cursor: pointer; }
.notif-area { position: relative; }
.notif-bell { position: relative; }
.notif-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--color-danger);
  color: white;
  font-size: 11px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
.main { flex: 1; padding: 24px; max-width: 1400px; margin: 0 auto; width: 100%; }
/* Контентная область едина для всех страниц (1400px): левый край
   контента на одном месте, при переходах ничего не дёргается. */
</style>
