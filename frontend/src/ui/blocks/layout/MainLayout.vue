<template>
  <div class="layout" :class="{ 'layout--fill': fill }">
    <a class="skip-link" href="#main-content">Перейти к содержимому</a>
    <div ref="shellRef" class="pp shell-top">
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
            <template v-for="item in navItems" :key="item.key">
              <!-- Группа страниц: значок раскрывает список разделов -->
              <!-- Информативный вид: раздел — обычная ссылка, его страницы — в левом меню -->
              <router-link v-if="item.items && sidebarOn" v-slot="{ href, navigate }" :to="item.items[0].to" custom>
                <a :href="href" :data-tip="item.label" :aria-current="isGroupActive(item) ? 'page' : null" @click="navigate">
                  <span class="icon" :data-icon="item.icon"><UiIcon :name="item.icon" /></span>
                  <span class="nav-label">{{ item.label }}</span>
                </a>
              </router-link>
              <div
                v-else-if="item.items"
                class="nav-group"
                :class="{ 'nav-group--open': openGroup === item.key }"
                @mouseenter="hoverOpen(item.key)"
                @mouseleave="hoverClose(item.key)"
              >
                <button
                  :ref="(el) => (groupButtons[item.key] = el)"
                  type="button"
                  class="nav-group-btn"
                  :data-tip="openGroup === item.key ? null : item.label"
                  :aria-expanded="openGroup === item.key"
                  :aria-controls="`nav-${item.key}`"
                  :aria-current="isGroupActive(item) ? 'page' : null"
                  @click="toggleGroup(item.key)"
                  @keydown.down.prevent="openAndFocus(item.key)"
                >
                  <span class="icon" :data-icon="item.icon"><UiIcon :name="item.icon" /></span>
                  <span class="nav-label">{{ item.label }}</span>
                  <span class="nav-caret" aria-hidden="true"></span>
                </button>
                <div
                  v-show="openGroup === item.key"
                  :id="`nav-${item.key}`"
                  class="menu-panel nav-menu"
                  role="menu"
                  :aria-label="item.label"
                  @keydown="onMenuKey($event, item.key)"
                >
                  <div class="nav-menu-title">{{ item.label }}</div>
                  <router-link
                    v-for="child in item.items"
                    :key="child.to"
                    v-slot="{ href, navigate }"
                    :to="child.to"
                    custom
                  >
                    <a
                      :href="href"
                      role="menuitem"
                      :aria-current="isSection(child) ? 'page' : null"
                      @click="navigate($event); closeGroup()"
                    >
                      <span class="icon" :data-icon="child.icon"><UiIcon :name="child.icon" /></span>
                      <span>{{ child.label }}</span>
                    </a>
                  </router-link>
                </div>
              </div>
              <!-- Одиночная страница -->
              <router-link v-else v-slot="{ href, navigate, isActive }" :to="item.to" custom>
                <a :href="href" :data-tip="item.label" :aria-current="isActive || isSection(item) ? 'page' : null" class="nav-link" @click="navigate">
                  <span class="icon" :data-icon="item.icon"><UiIcon :name="item.icon" /></span>
                  <span class="nav-label">{{ item.label }}</span>
                  <span v-if="item.key === 'messages' && chatUnread" class="nav-badge" :aria-label="`Непрочитанных сообщений: ${chatUnread}`">{{ chatUnread }}</span>
                </a>
              </router-link>
            </template>
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
            <details v-if="isLoggedIn" ref="accountRef" class="usermenu account">
              <summary class="account-btn" aria-label="Меню аккаунта">
                <UserAvatar :src="userAvatar" :name="userName" :size="30" />
              </summary>
              <div class="menu-panel account-panel" role="menu" aria-label="Аккаунт">
                <div class="account-who">
                  <strong>{{ userName || 'Аккаунт' }}</strong>
                  <small class="muted">{{ ROLE_NAMES[role] || '' }}</small>
                </div>
                <hr />
                <router-link v-for="link in accountLinks" :key="link.to" :to="link.to" role="menuitem" @click="closeAccount">
                  <span class="icon" :data-icon="link.icon"><UiIcon :name="link.icon" /></span> {{ link.label }}
                </router-link>
                <hr />
                <button type="button" role="menuitem" @click="closeAccount(); emit('logout')">
                  <span class="icon" data-icon="logout"><UiIcon name="logout" /></span> Выйти
                </button>
              </div>
            </details>
            <template v-else>
              <router-link to="/login" class="btn ghost">Войти</router-link>
              <router-link to="/register" class="btn primary nav-register">Регистрация</router-link>
            </template>
          </div>
        </div>
      </header>
    </div>
    <div class="body" :class="{ 'body--side': sidebarOn }">
      <aside v-if="sidebarOn" class="pp side-nav" :aria-label="sideSection ? `Страницы раздела «${sideSection.label}»` : 'Разделы'">
        <div class="side-nav-inner">
          <div class="side-nav-title">{{ sideSection ? sideSection.label : 'Разделы' }}</div>
          <router-link
            v-for="link in sideLinks"
            :key="link.to"
            v-slot="{ href, navigate }"
            :to="link.to"
            custom
          >
            <a :href="href" class="side-link" :aria-current="isSection(link) ? 'page' : null" @click="navigate">
              <span class="icon" :data-icon="link.icon"><UiIcon :name="link.icon" /></span>
              <span class="grow">{{ link.label }}</span>
              <span v-if="link.to === '/messages' && chatUnread" class="side-badge" :aria-label="`Непрочитанных сообщений: ${chatUnread}`">{{ chatUnread }}</span>
            </a>
          </router-link>
        </div>
      </aside>
      <main id="main-content" class="main" tabindex="-1">
        <slot />
      </main>
    </div>
    <div v-if="!fill" class="pp">
      <footer class="site-footer">
        <div class="wrap footer-inner">
          <span>© SHAD — расписание, тесты, доски и блог репетиторов</span>
          <nav class="footer-nav" aria-label="Ссылки">
            <router-link v-if="isLoggedIn" to="/blog">Блог</router-link>
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
// Шапка всегда видна (sticky на любом экране); её высота — в --shell-h для рабочих экранов (доска).
import { computed, ref, reactive, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import NotificationPanel from './NotificationPanel.vue'
import { UiIcon, UserAvatar } from '../../components/index.js'
import { useChat, useNavMode, useNotifications, useTheme, useUser } from '../../composables/index.js'

const props = defineProps({
  isLoggedIn: { type: Boolean, default: false },
  role: { type: String, default: '' },
  // Рабочий экран на всю ширину без подвала (доска): контент сам занимает высоту под шапкой.
  fill: { type: Boolean, default: false },
})
const emit = defineEmits(['logout'])
const route = useRoute()
const { theme, toggleTheme } = useTheme()
const { userName, userAvatar } = useUser()
// Чат: соединение для репетитора и ученика, число непрочитанных — на пункте «Сообщения».
const { chatUnread } = useChat()

// Разделы по ролям: в шапке — разделы, внутри — их страницы (левое меню или выпадающий список).
// Профиль и настройки — в меню аккаунта справа, не разделом.
const NAV = {
  guest: [
    { key: 'how', to: '/how-it-works', label: 'Как это работает', icon: 'info' },
    { key: 'for-tutors', to: '/for-tutors', label: 'Репетиторам', icon: 'users' },
    { key: 'faq', to: '/faq', label: 'Вопросы', icon: 'chat' },
  ],
  student: [
    {
      key: 'schedule', label: 'Расписание', icon: 'calendar',
      items: [
        { to: '/schedule', label: 'Расписание', icon: 'calendar' },
        { to: '/upcoming', label: 'Ближайшие уроки', icon: 'clock' },
      ],
    },
    { key: 'tutors', to: '/tutors', label: 'Репетиторы', icon: 'users' },
    { key: 'messages', to: '/messages', label: 'Сообщения', icon: 'chat' },
    {
      key: 'tools', label: 'Инструменты', icon: 'board',
      items: [
        { to: '/boards', label: 'Доски', icon: 'board' },
        { to: '/testing', label: 'Тесты', icon: 'tests' },
        { to: '/blog', label: 'Блог', icon: 'blog', exclude: ['/blog/manage'] },
      ],
    },
  ],
  tutor: [
    {
      key: 'schedule', label: 'Расписание', icon: 'calendar',
      items: [
        { to: '/schedule', label: 'Расписание', icon: 'calendar' },
        { to: '/bookings', label: 'Брони', icon: 'clock' },
        { to: '/upcoming', label: 'Ближайшие уроки', icon: 'clock' },
      ],
    },
    { key: 'students', to: '/students', label: 'Ученики', icon: 'users' },
    { key: 'messages', to: '/messages', label: 'Сообщения', icon: 'chat' },
    {
      key: 'tools', label: 'Инструменты', icon: 'board',
      items: [
        { to: '/boards', label: 'Доски', icon: 'board' },
        { to: '/testing', label: 'Тесты', icon: 'tests' },
        { to: '/blog', label: 'Блог', icon: 'blog', exclude: ['/blog/manage'] },
        { to: '/blog/manage', label: 'Мой блог', icon: 'edit' },
      ],
    },
    {
      key: 'finance', label: 'Финансы', icon: 'wallet',
      items: [
        { to: '/payments', label: 'Оплаты', icon: 'wallet' },
        { to: '/statistics', label: 'Статистика', icon: 'chart' },
      ],
    },
  ],
  admin: [
    {
      key: 'admin', label: 'Управление', icon: 'shield',
      items: [
        { to: '/admin', label: 'Сводка', icon: 'chart', exact: true },
        { to: '/admin/users', label: 'Пользователи', icon: 'users' },
        { to: '/admin/db', label: 'База данных', icon: 'sliders' },
        { to: '/admin/audit', label: 'Журнал действий', icon: 'clock' },
      ],
    },
    {
      key: 'site', label: 'Сайт', icon: 'blog',
      items: [
        { to: '/admin/site', label: 'Гостевая страница', icon: 'info' },
        { to: '/blog/manage', label: 'Блог владельца', icon: 'edit' },
        { to: '/blog', label: 'Блоги репетиторов', icon: 'blog', exclude: ['/blog/manage'] },
      ],
    },
    {
      key: 'system', label: 'Система', icon: 'sliders',
      items: [
        { to: '/admin/system', label: 'Состояние', icon: 'chart' },
        { to: '/admin/logs', label: 'Логи', icon: 'info' },
        { to: '/admin/key', label: 'Ключ входа', icon: 'key' },
      ],
    },
  ],
}
// Страницы аккаунта: меню справа по нажатию на аватар.
const ACCOUNT = {
  tutor: [{ to: '/profile', label: 'Профиль', icon: 'user' }, { to: '/settings', label: 'Настройки', icon: 'sliders' }],
  student: [{ to: '/profile', label: 'Профиль', icon: 'user' }, { to: '/student-settings', label: 'Настройки', icon: 'sliders' }],
  admin: [{ to: '/profile', label: 'Профиль', icon: 'user' }],
}
const accountLinks = computed(() => ACCOUNT[props.role] || [{ to: '/profile', label: 'Профиль', icon: 'user' }])
const ROLE_NAMES = { tutor: 'Репетитор', student: 'Ученик', admin: 'Владелец' }
const accountRef = ref(null)
const closeAccount = () => { if (accountRef.value) accountRef.value.open = false }
watch(() => route.fullPath, closeAccount)

const navItems = computed(() => (props.isLoggedIn ? NAV[props.role] || [] : NAV.guest))

// --- Левое меню (информативный вид, широкий экран): страницы текущего раздела ---
const { sidebarAllowed } = useNavMode()
const sidebarOn = computed(() => props.isLoggedIn && !props.fill && sidebarAllowed.value && navItems.value.length > 0)
// Страницы вне меню относятся к ближайшему разделу: урок — к расписанию, доска — к занятиям.
const EXTRA_SECTIONS = { '/lessons': '/schedule' }
const sideSection = computed(() => {
  const own = navItems.value.find((item) => (item.items ? isGroupActive(item) : isSection(item)))
  if (own) return own
  const extra = Object.entries(EXTRA_SECTIONS).find(([prefix]) => route.path.startsWith(prefix))
  if (!extra) return null
  return navItems.value.find((item) => (item.items || [item]).some((child) => (child.section || child.to) === extra[1])) || null
})
// Раздел из одной страницы показывает её саму; без раздела (главная, уведомления) — все разделы.
const sideLinks = computed(() => {
  const section = sideSection.value
  if (section) return section.items || [section]
  return navItems.value.map((item) => (item.items ? { ...item.items[0], label: item.label, icon: item.icon } : item))
})

// Раздел подсвечивается и на вложенных страницах (тест, доска, запись блога).
function isSection(item) {
  const base = item.section || item.to
  if (item.exclude?.some((prefix) => route.path === prefix || route.path.startsWith(prefix + '/'))) return false
  if (item.exact) return route.path === base
  return route.path === base || route.path.startsWith(base + '/')
}
function isGroupActive(group) {
  return group.items.some((child) => isSection(child))
}

// --- Раскрытие групп: наведение (мышь), нажатие (сенсор/клавиатура), Escape, щелчок вне ---
const openGroup = ref('')
const groupButtons = reactive({})
const canHover = typeof window !== 'undefined' && window.matchMedia?.('(hover: hover) and (pointer: fine)').matches
let hoverTimer = 0
// Группа, раскрытая наведением: щелчок по ней её не закрывает, а закрепляет
// (иначе мышь раскрывает при наведении, а щелчок тут же сворачивает).
let openedByHover = ''

function toggleGroup(key) {
  if (openGroup.value === key && openedByHover === key) {
    openedByHover = ''
    return
  }
  openedByHover = ''
  openGroup.value = openGroup.value === key ? '' : key
}
function closeGroup() {
  openGroup.value = ''
  openedByHover = ''
}
function hoverOpen(key) {
  if (!canHover) return
  clearTimeout(hoverTimer)
  if (openGroup.value !== key) openedByHover = key
  openGroup.value = key
}
function hoverClose(key) {
  if (!canHover) return
  clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    if (openGroup.value === key && openedByHover === key) closeGroup()
  }, 180)
}
function menuItems(key) {
  return [...(document.getElementById(`nav-${key}`)?.querySelectorAll('[role="menuitem"]') || [])]
}
function openAndFocus(key) {
  openGroup.value = key
  requestAnimationFrame(() => menuItems(key)[0]?.focus())
}
function onMenuKey(event, key) {
  const items = menuItems(key)
  const index = items.indexOf(document.activeElement)
  if (event.key === 'Escape') {
    event.preventDefault()
    closeGroup()
    groupButtons[key]?.focus()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    items[(index + 1) % items.length]?.focus()
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    items[(index - 1 + items.length) % items.length]?.focus()
  } else if (event.key === 'Tab') {
    closeGroup()
  }
}
function onDocPointer(event) {
  if (openGroup.value && !(event.target instanceof Element && event.target.closest('.nav-group'))) closeGroup()
}
function onDocKey(event) {
  if (event.key === 'Escape' && openGroup.value) {
    const key = openGroup.value
    closeGroup()
    groupButtons[key]?.focus()
  }
}
watch(() => route.fullPath, closeGroup)

// --- Высота шапки для рабочих экранов (доска занимает высоту под ней) ---
const shellRef = ref(null)
let shellObserver = null

const navLinks = ref(null)
onMounted(() => {
  const active = navLinks.value?.querySelector('[aria-current="page"]')
  if (active) navLinks.value.scrollLeft = Math.max(0, active.offsetLeft - navLinks.value.offsetLeft - 16)
  document.addEventListener('pointerdown', onDocPointer)
  document.addEventListener('keydown', onDocKey)
  if (shellRef.value && typeof ResizeObserver !== 'undefined') {
    shellObserver = new ResizeObserver(([entry]) => {
      document.documentElement.style.setProperty('--shell-h', `${Math.round(entry.contentRect.height)}px`)
    })
    shellObserver.observe(shellRef.value)
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocPointer)
  document.removeEventListener('keydown', onDocKey)
  shellObserver?.disconnect()
  clearTimeout(hoverTimer)
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
.layout--fill .body { display: flex; flex-direction: column; }
/* Шапка всегда видна: и на телефоне, и на компьютере. */
.shell-top { position: sticky; top: 0; z-index: 100; }
.pp .site-header { position: static; }
.pp .brand-name { letter-spacing: .04em; }
.notif-area { position: relative; }
.pp .nav-main a.nav-link { position: relative; }
.nav-badge { position: absolute; top: 6px; right: 2px; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: var(--accent); color: var(--accent-ink); font-size: 10px; font-weight: 700; line-height: 16px; text-align: center; }
.account-btn { display: inline-flex; align-items: center; height: var(--ctl); padding: 0 4px; border-radius: 999px; }
.pp .usermenu.account summary::after { display: none; }
.account-btn:hover :deep(.user-avatar) { box-shadow: 0 0 0 2px var(--accent-soft); }
.account-panel { min-width: 220px; }
.account-who { display: grid; gap: 2px; padding: 8px 12px 4px; }
.notif-badge { position: absolute; top: 1px; right: 1px; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: var(--danger); color: var(--accent-ink); font-size: 10px; font-weight: 700; line-height: 16px; text-align: center; }
.pp .header-actions .btn.icon { width: var(--ctl); padding: 0; border: 1px solid var(--line); }
.body { flex: 1; display: flex; min-width: 0; }
.main { flex: 1; padding: 40px 24px 80px; max-width: 1208px; margin: 0 auto; width: 100%; min-width: 0; }
.body--side .main { padding-left: 32px; }
/* Левое меню раздела: одинаковое место на любой странице, прилипает под шапкой. */
.side-nav { width: 232px; flex: none; border-right: 1px solid var(--line); background: var(--bg); }
.side-nav-inner { position: sticky; top: var(--shell-h, 64px); display: grid; gap: 2px; padding: 28px 14px; max-height: calc(100dvh - var(--shell-h, 64px)); overflow-y: auto; }
.side-nav-title { padding: 0 12px 10px; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 600; }
.pp .side-link { display: flex; align-items: center; gap: 12px; padding: 9px 12px; border-radius: 10px; color: var(--muted); font-size: 14.5px; text-decoration: none; transition: background var(--t) var(--ease), color var(--t) var(--ease); }
.pp .side-link:hover { background: var(--surface); color: var(--text); text-decoration: none; }
.pp .side-link[aria-current="page"] { background: var(--accent-soft); color: var(--text); font-weight: 500; }
.pp .side-link .icon { display: inline-flex; color: inherit; }
.pp .side-link[aria-current="page"] .icon { color: var(--accent); }
.pp .side-link .icon svg { width: 19px; height: 19px; }
.side-link .grow { flex: 1; }
.side-badge { min-width: 20px; height: 20px; padding: 0 6px; border-radius: 999px; background: var(--accent); color: var(--accent-ink); font-size: 11px; font-weight: 700; display: inline-grid; place-items: center; }
.main:focus { outline: none; }
.layout--fill .main { padding: 0; max-width: none; display: flex; flex-direction: column; }

/* Группа меню: кнопка в стиле пунктов навигации + выпадающая панель эталона (.menu-panel). */
/* Меню с группами умещается без прокрутки: снимаем прокрутку и маску краёв эталона —
   маска обрезала бы выпадающие панели групп. */
.pp .nav-main { overflow: visible; mask-image: none; -webkit-mask-image: none; }
.nav-group { position: relative; display: flex; }
.pp .nav-group-btn {
  display: inline-flex; align-items: center; gap: 4px; padding: 0 12px;
  font: inherit; font-size: 15px; color: var(--muted); background: none; border: 0;
  border-bottom: 2px solid transparent; margin-bottom: -1px; cursor: pointer;
  transition: color var(--t) var(--ease), border-color var(--t) var(--ease);
}
.pp .nav-group-btn:hover, .nav-group--open .nav-group-btn { color: var(--text); }
.pp .nav-group-btn[aria-current="page"] { color: var(--text); border-bottom-color: var(--accent); }
.pp .nav-group-btn .icon { color: var(--muted); transition: color var(--t) var(--ease); }
.pp .nav-group-btn:hover .icon, .nav-group--open .nav-group-btn .icon { color: var(--text); }
.pp .nav-group-btn[aria-current="page"] .icon { color: var(--accent); }
.nav-caret {
  width: 6px; height: 6px; margin-left: 2px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor;
  transform: rotate(45deg) translateY(-2px); opacity: .7; transition: transform var(--t) var(--ease);
}
.nav-group--open .nav-caret { transform: rotate(-135deg) translateY(-1px); }
.pp .nav-menu { left: 0; right: auto; top: calc(100% + 4px); min-width: 220px; }
.nav-menu-title { padding: 6px 12px 4px; font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }
/* Пункты панели — полноценные строки меню, а не квадратные значки шапки (правила .nav-main a эталона). */
.pp .nav-menu a {
  display: flex; width: auto; height: auto; justify-content: flex-start; gap: 10px;
  padding: 10px 12px; margin: 0; border-bottom: 0; font-size: 14px; color: var(--text); white-space: nowrap;
}
.pp .nav-menu a:hover { background: var(--surface-2); }
.pp .nav-menu .icon { display: inline-flex; }
.pp .nav-menu .icon svg { width: 18px; height: 18px; }
.pp .nav-menu a[aria-current="page"] { color: var(--accent); background: var(--surface-2); }
.pp .nav-menu a[aria-current="page"] .icon { color: var(--accent); }

@media (max-width: 720px) {
  .main { padding: 28px 16px 56px; }
  .layout--fill .main { padding: 0; }
  .nav-register { display: none !important; }
  .pp .nav-group-btn { padding: 0 10px; font-size: 14px; }
  /* На телефоне панель группы — во всю ширину под шапкой. */
  .pp .nav-menu { position: fixed; left: 8px; right: 8px; top: calc(var(--shell-h, 104px) + 4px); min-width: 0; }
}
/* Очень узкий экран: подписи меню не помещаются — только значки (подписи остаются для экранного диктора). */
@media (max-width: 480px) {
  .pp .nav-main { gap: 0; justify-content: space-between; }
  .pp .nav-main .icon { display: inline-flex; }
  .pp .nav-main .nav-label {
    position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
  }
  .pp .nav-group-btn, .pp .nav-main > a { padding: 0 8px; }
  .pp .nav-menu .icon { display: inline-flex; }
}
</style>
