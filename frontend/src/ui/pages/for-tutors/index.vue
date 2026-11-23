<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <PublicPage title="Репетиторам" subtitle="Ведение учеников, расписания и оплат в одном месте">
      <section class="guest">
        <div class="feature-card">
          <span class="feature-icon">📅</span>
          <h3 class="feature-title">Расписание и брони</h3>
          <p class="feature-desc">Настройте повторяющиеся окна доступности — студенты увидят только разрешённые слоты.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">👥</span>
          <h3 class="feature-title">Ученики и связь</h3>
          <p class="feature-desc">Персональные ставки, скидки и правила самозаписи для каждой связи.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">💰</span>
          <h3 class="feature-title">Оплаты и статистика</h3>
          <p class="feature-desc">Отмечайте оплату, следите за задолженностями и выручкой за период.</p>
        </div>
      </section>

      <section class="card cta">
        <h2 class="card-title">Начните работать</h2>
        <p class="placeholder">Зарегистрируйтесь как репетитор, чтобы настроить профиль и пригласить первого ученика.</p>
        <router-link to="/register" class="btn btn--pri">Зарегистрироваться</router-link>
      </section>

      <section class="card">
        <h2 class="card-title">Раздел в разработке</h2>
        <p class="placeholder">Здесь появятся тарифы, примеры расчёта стоимости и ответы на вопросы репетиторов.</p>
      </section>
    </PublicPage>
  </MainLayout>
</template>

<script setup>
import MainLayout from '../../blocks/layout/MainLayout.vue'
import PublicPage from '../../blocks/public/PublicPage.vue'
import { useUser, useLogout } from '../../composables/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
</script>

<style scoped>
.guest {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}
.feature-card {
  padding: 24px;
  background: var(--color-white);
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--color-gray-200);
}
.feature-icon { font-size: 32px; }
.feature-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin: 8px 0 6px; }
.feature-desc { font-size: 14px; color: var(--color-gray-600); line-height: 1.5; margin: 0; }
.card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  padding: 24px;
  margin-bottom: 16px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin-bottom: 8px; }
.placeholder { font-size: 14px; color: var(--color-gray-500); margin: 0 0 12px; }
.cta { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
.cta .btn { margin-top: 8px; }
</style>
