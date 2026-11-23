<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="home-page">
      <template v-if="isLoggedIn">
        <div class="page-header">
          <div class="page-title-row">
            <h1 class="page-title">Главная</h1>
          </div>
        </div>
        <div class="home-menu">
          <router-link to="/profile" class="menu-card">
            <span class="menu-icon">⚙️</span>
            <span class="menu-label">Профиль</span>
          </router-link>
          <router-link to="/schedule" class="menu-card">
            <span class="menu-icon">📅</span>
            <span class="menu-label">Расписание</span>
          </router-link>
          <router-link to="/notifications" class="menu-card">
            <span class="menu-icon">🔔</span>
            <span class="menu-label">Уведомления</span>
          </router-link>
          <router-link v-if="role === 'student'" to="/tutors" class="menu-card">
            <span class="menu-icon">👤</span>
            <span class="menu-label">Репетиторы</span>
          </router-link>
          <router-link v-if="role === 'tutor'" to="/students" class="menu-card">
            <span class="menu-icon">👥</span>
            <span class="menu-label">Ученики</span>
          </router-link>
          <router-link v-if="role === 'tutor'" to="/bookings" class="menu-card">
            <span class="menu-icon">📋</span>
            <span class="menu-label">Брони</span>
          </router-link>
          <router-link v-if="role === 'tutor'" to="/payments" class="menu-card">
            <span class="menu-icon">💰</span>
            <span class="menu-label">Оплаты</span>
          </router-link>
          <router-link v-if="role === 'admin'" to="/admin" class="menu-card">
            <span class="menu-icon">🛡️</span>
            <span class="menu-label">Управление</span>
          </router-link>
        </div>
      </template>

      <template v-else>
        <div class="guest">
          <section class="hero">
            <h1 class="hero-title">SHAD Tutoring</h1>
            <p class="hero-subtitle">Удобная платформа для организации занятий с репетиторами</p>
          </section>

          <section class="features">
            <div class="feature-card">
              <span class="feature-icon">📅</span>
              <h3 class="feature-title">Расписание</h3>
              <p class="feature-desc">Просматривайте расписание занятий, создавайте и отменяйте уроки в несколько кликов</p>
            </div>
            <div class="feature-card">
              <span class="feature-icon">🤝</span>
              <h3 class="feature-title">Связь с репетитором</h3>
              <p class="feature-desc">Студенты находят репетиторов, репетиторы управляют своими учениками</p>
            </div>
            <div class="feature-card">
              <span class="feature-icon">📋</span>
              <h3 class="feature-title">Бронирование</h3>
              <p class="feature-desc">Репетиторы настраивают доступные слоты, ученики записываются на удобное время</p>
            </div>
          </section>
        </div>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
</script>

<style scoped>
.home-page { display: flex; flex-direction: column; }
.home-menu { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
.menu-card {
  display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 24px;
  background: white; border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  text-decoration: none; transition: all 150ms; border: 1px solid var(--color-gray-200);
}
.menu-card:hover { box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-color: var(--color-accent); text-decoration: none; }
.menu-icon { font-size: 32px; }
.menu-label { font-size: 16px; font-weight: 500; color: var(--color-gray-800); }

.guest { max-width: 900px; margin: 0 auto; }
.hero { text-align: center; padding: 48px 0 40px; }
.hero-title { font-size: 36px; font-weight: 700; color: var(--color-primary); margin-bottom: 12px; }
.hero-subtitle { font-size: 18px; color: var(--color-text-muted); }
.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }
.feature-card {
  padding: 24px; background: white; border-radius: 12px;
  border: 1px solid var(--color-gray-200); box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.feature-icon { font-size: 28px; }
.feature-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin: 8px 0 6px; }
.feature-desc { font-size: 14px; color: var(--color-text-muted); line-height: 1.5; margin: 0; }
</style>
