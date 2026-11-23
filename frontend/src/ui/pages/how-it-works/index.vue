<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <PublicPage title="Как это работает" subtitle="Путь от выбора репетитора до проведения урока">
      <section class="guest">
        <div class="feature-card">
          <span class="feature-icon">1</span>
          <h3 class="feature-title">Выберите репетитора</h3>
          <p class="feature-desc">Найдите репетитора по персональному номеру или из каталога и отправьте заявку на связь.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">2</span>
          <h3 class="feature-title">Запишитесь на удобное время</h3>
          <p class="feature-desc">Репетитор открывает слоты брони — вы видите свободные окна и записываетесь в пару кликов.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">3</span>
          <h3 class="feature-title">Займись онлайн</h3>
          <p class="feature-desc">Ссылка на занятие появляется в уроке за назначенное время — всё в одном расписании.</p>
        </div>
      </section>

      <section class="card">
        <h2 class="card-title">Раздел в разработке</h2>
        <p class="placeholder">Здесь появятся подробные инструкции: скриншоты, частые сценарии записи и отмены, правила работы со временем.</p>
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
.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full, 50%);
  background: var(--color-accent);
  color: var(--color-white);
  font-size: 18px;
  font-weight: 700;
}
.feature-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin: 8px 0 6px; }
.feature-desc { font-size: 14px; color: var(--color-gray-600); line-height: 1.5; margin: 0; }
.card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  padding: 24px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin-bottom: 8px; }
.placeholder { font-size: 14px; color: var(--color-gray-500); margin: 0; }
</style>
