<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <PublicPage title="Вопросы и ответы" subtitle="Коротко о записи, отмене, оплате и учетной записи">
      <section class="card">
        <h2 class="card-title">Как записаться на урок?</h2>
        <p class="placeholder">Через страницу «Расписание»: выберите свободное окно репетитора и подтвердите запись.</p>
      </section>
      <section class="card">
        <h2 class="card-title">Можно ли отменить занятие?</h2>
        <p class="placeholder">Да — в деталях урока, если до начала остаётся больше времени, чем допускает репетитор.</p>
      </section>
      <section class="card">
        <h2 class="card-title">Как отмечается оплата?</h2>
        <p class="placeholder">Репетитор отмечает оплату в реестре «Оплаты»; статус виден обеим сторонам.</p>
      </section>
      <section class="card">
        <h2 class="card-title">Раздел в разработке</h2>
        <p class="placeholder">Полный список вопросов появится здесь — пока используйте уведомления и поддержку репетитора.</p>
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
.card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  padding: 20px 24px;
  margin-bottom: 16px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin-bottom: 6px; }
.placeholder { font-size: 14px; color: var(--color-gray-600); line-height: 1.5; margin: 0; }
</style>
