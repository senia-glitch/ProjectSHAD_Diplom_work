<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="login-page">
      <div class="login-card">
        <p class="auth-eyebrow">SHAD Tutoring</p>
        <h1 class="login-title">Вход</h1>
        <p class="auth-description">Рады видеть вас снова. Войдите, чтобы продолжить.</p>
        <form class="login-form" @submit.prevent="handleSubmit" novalidate>
          <div class="form-group" :class="{ 'has-error': errors.login }">
            <label for="login">Логин</label>
            <input
              id="login"
              v-model="form.login"
              type="text"
              placeholder="Введите логин"
              autocomplete="username"
              :class="{ error: errors.login }"
            />
            <span v-if="errors.login" class="field-error">{{ errors.login }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': errors.password }">
            <label for="password">Пароль</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              placeholder="Введите пароль"
              autocomplete="current-password"
              :class="{ error: errors.password }"
            />
            <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
          </div>
          <div v-if="serverError" class="server-error" role="alert">{{ serverError }}</div>
          <button type="submit" class="btn btn--primary btn--full" :disabled="loading">
            {{ loading ? 'Вход...' : 'Войти' }}
          </button>
        </form>
        <p class="login-footer">
          Нет аккаунта?
          <router-link to="/register">Зарегистрироваться</router-link>
        </p>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { loginUser } from '../../../logic/actions/index.js'

const router = useRouter()
const route = useRoute()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()

const form = reactive({ login: '', password: '' })
const errors = reactive({ login: '', password: '' })
const serverError = ref('')
const loading = ref(false)

function validate() {
  errors.login = ''
  errors.password = ''
  let valid = true

  if (!form.login.trim()) {
    errors.login = 'Обязательное поле'
    valid = false
  }

  if (!form.password) {
    errors.password = 'Обязательное поле'
    valid = false
  }

  return valid
}

async function handleSubmit() {
  serverError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    await loginUser({ username: form.login, password: form.password })
    // Возврат туда, откуда guard отправил на логин. Принимаем только
    // внутренние пути вида /..., иначе — на главную.
    const back = route.query.redirect
    const target =
      typeof back === 'string' && /^\/(?!\/)/.test(back) ? back : '/'
    router.push(target)
  } catch (err) {
    serverError.value = err.message || 'Ошибка сервера'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
.login-card {
  width: 100%;
  max-width: 400px;
  padding: var(--spacing-8);
  background: var(--color-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-gray-200);
}
.login-title {
  text-align: center;
  margin-bottom: var(--spacing-6);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary);
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}
.login-footer {
  text-align: center;
  margin-top: var(--spacing-4);
  font-size: 13px;
  color: var(--color-gray-600);
}

.login-page { padding: 24px 0; }
.login-card { max-width: 440px; box-shadow: none; padding: 32px; }
.login-title { text-align: left; font-size: 28px; font-weight: 600; margin-bottom: 8px; letter-spacing: -.02em; }
.auth-eyebrow { color: var(--accent); text-transform: uppercase; font-size: 10px; font-weight: 600; letter-spacing: .12em; margin-bottom: 16px; }
.auth-description { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
.login-footer { border-top: 1px solid var(--line); padding-top: 16px; margin-top: 24px; }
@media (max-width: 600px) { .login-card { padding: 24px; } .login-page { padding: 0; } }
</style>
