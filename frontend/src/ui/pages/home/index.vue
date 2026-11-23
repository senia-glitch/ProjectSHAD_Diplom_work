<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <template v-if="isLoggedIn">
      <div class="page-header">
        <p class="eyebrow">Ваш кабинет</p>
        <h1 class="page-title">{{ userName ? `Здравствуйте, ${userName}` : 'Рабочее пространство' }}</h1>
        <p class="page-desc">Занятия, люди и важные детали — всё под рукой.</p>
      </div>
      <section class="workspace-intro">
        <div class="intro-icon"><UiIcon name="calendar" /></div>
        <div><h2>Планы на неделю</h2><p>Откройте расписание, чтобы посмотреть занятия{{ role === 'tutor' ? ' или запланировать новый урок' : '' }}.</p></div>
        <router-link to="/schedule" class="btn btn--pri">К расписанию <UiIcon name="arrowRight" /></router-link>
      </section>
      <h2 class="section-heading">Быстрый переход</h2>
      <div class="home-menu">
        <router-link v-for="item in menu" :key="item.to" :to="item.to" class="menu-card">
          <span class="menu-icon"><UiIcon :name="item.icon" /></span>
          <span class="menu-copy"><span class="menu-label">{{ item.label }}</span><span class="menu-description">{{ item.description }}</span></span>
          <UiIcon name="arrowRight" class="menu-arrow" />
        </router-link>
      </div>
    </template>
    <template v-else>
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">SHAD Tutoring</p>
          <h1>Больше времени<br />на сами занятия</h1>
          <p class="hero-subtitle">Расписание, запись на уроки и связь с репетитором — в одном спокойном рабочем пространстве.</p>
          <div class="hero-actions"><router-link to="/register" class="btn btn--pri">Создать аккаунт <UiIcon name="arrowRight" /></router-link><router-link to="/how-it-works" class="btn btn--gry">Как это работает</router-link></div>
        </div>
        <div class="hero-note">
          <span class="intro-icon"><UiIcon name="calendar" /></span>
          <h2>Учиться и преподавать проще, когда всё на своих местах.</h2>
          <ul><li><UiIcon name="check" />Единое расписание занятий</li><li><UiIcon name="check" />Удобная запись на свободное время</li><li><UiIcon name="check" />Участники, ссылки и оплаты рядом</li></ul>
        </div>
      </section>
      <section class="features" aria-label="Возможности платформы">
        <article v-for="item in features" :key="item.title" class="feature-card"><span class="menu-icon"><UiIcon :name="item.icon" /></span><h2>{{ item.title }}</h2><p>{{ item.description }}</p></article>
      </section>
    </template>
  </MainLayout>
</template>

<script setup>
import { computed } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon } from '../../components/index.js'
import { useUser, useLogout } from '../../composables/index.js'

const { role, isLoggedIn, userName } = useUser()
const { handleLogout } = useLogout()
const menu = computed(() => [
  { to: '/profile', icon: 'user', label: 'Профиль', description: 'Личные данные и код для связи' },
  { to: '/notifications', icon: 'bell', label: 'Уведомления', description: 'Изменения и события занятий' },
  ...(role.value === 'tutor' ? [
    { to: '/students', icon: 'users', label: 'Ученики', description: 'Участники и персональные условия' },
    { to: '/bookings', icon: 'clock', label: 'Брони', description: 'Окна для записи и правила доступа' },
    { to: '/statistics', icon: 'chart', label: 'Статистика', description: 'Нагрузка и результаты за период' },
    { to: '/payments', icon: 'wallet', label: 'Оплаты', description: 'Стоимость занятий и расчёты' },
  ] : []),
  ...(role.value === 'student' ? [{ to: '/tutors', icon: 'users', label: 'Репетиторы', description: 'Ваши преподаватели и условия занятий' }] : []),
  ...(role.value === 'admin' ? [{ to: '/admin', icon: 'shield', label: 'Управление', description: 'Пользователи и состояние системы' }] : []),
])
const features = [
  { icon: 'calendar', title: 'Видеть всю неделю', description: 'Занятия и свободные окна в наглядном расписании. Переключайтесь между неделей и календарём.' },
  { icon: 'users', title: 'Оставаться на связи', description: 'Ученики и репетиторы, персональные условия и ссылки на занятия в одном месте.' },
  { icon: 'clock', title: 'Планировать без суеты', description: 'Репетитор открывает удобные часы, ученик выбирает подходящее время для записи.' },
]
</script>

<style scoped>
.eyebrow { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; font-weight: 600; color: var(--accent); margin-bottom: 8px; }
.workspace-intro { display: flex; align-items: center; gap: 24px; padding: 24px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); margin-bottom: 32px; }
.intro-icon { width: 48px; height: 48px; display: grid; place-items: center; background: var(--accent-soft); color: var(--accent); border-radius: 12px; flex-shrink: 0; }
.intro-icon .ui-icon { width: 24px; height: 24px; }
.workspace-intro h2 { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.workspace-intro p { font-size: 13px; color: var(--muted); }
.workspace-intro > .btn { margin-left: auto; white-space: nowrap; }
.section-heading { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 500; margin-bottom: 16px; }
.home-menu { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.menu-card { display: flex; align-items: center; gap: 16px; padding: 24px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); color: var(--text); transition: border-color var(--t), transform var(--t); }
.menu-card:hover { border-color: var(--accent); transform: translateY(-2px); text-decoration: none; }
.menu-icon { display: inline-flex; color: var(--accent); flex-shrink: 0; }
.menu-copy { display: flex; flex-direction: column; gap: 4px; }
.menu-label { font-size: 14px; font-weight: 600; }
.menu-description { font-size: 12px; color: var(--muted); }
.menu-arrow { width: 16px; height: 16px; color: var(--muted); margin-left: auto; }
.hero { display: grid; grid-template-columns: 1.2fr 1fr; gap: 64px; padding: 48px 0 64px; align-items: center; }
.hero h1 { font-size: clamp(32px, 4vw, 48px); line-height: 1.15; letter-spacing: -.035em; font-weight: 600; margin: 16px 0 24px; }
.hero-subtitle { max-width: 44ch; font-size: 16px; color: var(--muted); }
.hero-actions { display: flex; gap: 12px; margin-top: 32px; flex-wrap: wrap; }
.hero-note { padding: 32px; border: 1px solid var(--line); border-radius: 16px; background: var(--surface); }
.hero-note h2 { font-size: 22px; font-weight: 500; line-height: 1.45; margin: 24px 0; }
.hero-note ul { display: flex; flex-direction: column; gap: 16px; }
.hero-note li { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--muted); }
.hero-note li .ui-icon { color: var(--accent); width: 16px; height: 16px; }
.features { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.feature-card { padding: 24px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: var(--surface); }
.feature-card h2 { font-size: 16px; font-weight: 600; margin: 16px 0 8px; }
.feature-card p { color: var(--muted); font-size: 13px; }
@media (max-width: 950px) { .home-menu { grid-template-columns: repeat(2, minmax(0, 1fr)); } .hero { gap: 24px; } }
@media (max-width: 700px) {
  .workspace-intro { flex-wrap: wrap; gap: 16px; }
  .workspace-intro > .btn { margin-left: 0; }
  .home-menu, .hero, .features { grid-template-columns: minmax(0, 1fr); }
  .hero { padding: 16px 0 32px; }
  .hero-note { padding: 24px; }
  .menu-card { padding: 16px; }
}
</style>
