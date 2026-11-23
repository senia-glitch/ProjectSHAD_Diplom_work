<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="register-page">
      <div class="register-card">
        <h1 class="register-title">Регистрация</h1>
        <form class="register-form" @submit.prevent="handleSubmit" novalidate>
        <div class="form-group" :class="{ 'has-error': errors.username }">
          <label for="username">Логин</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="Введите логин"
            autocomplete="username"
            :class="{ error: errors.username }"
          />
          <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
        </div>

        <div class="form-group" :class="{ 'has-error': errors.full_name }">
          <label for="full_name">ФИО</label>
          <input
            id="full_name"
            v-model="form.full_name"
            type="text"
            placeholder="Иванов Иван Иванович"
            autocomplete="name"
            :class="{ error: errors.full_name }"
          />
          <span v-if="errors.full_name" class="field-error">{{ errors.full_name }}</span>
        </div>

        <div class="form-group" :class="{ 'has-error': errors.email }">
          <label for="email">Почта</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            placeholder="Введите email"
            autocomplete="email"
            :class="{ error: errors.email }"
          />
          <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
        </div>

        <div class="form-group" :class="{ 'has-error': errors.password }">
          <label for="password">Пароль</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            placeholder="Не менее 8 символов"
            autocomplete="new-password"
            :class="{ error: errors.password }"
          />
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </div>

        <div class="form-group" :class="{ 'has-error': errors.confirmPassword }">
          <label for="confirmPassword">Подтвердите пароль</label>
          <input
            id="confirmPassword"
            v-model="form.confirmPassword"
            type="password"
            placeholder="Повторите пароль"
            autocomplete="new-password"
            :class="{ error: errors.confirmPassword }"
          />
          <span v-if="errors.confirmPassword" class="field-error">{{ errors.confirmPassword }}</span>
        </div>

        <div class="form-group">
          <label for="role">Роль</label>
          <select id="role" v-model="form.role" autocomplete="off">
            <option v-for="r in REGISTER_ROLES" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>

        <div v-if="serverError" class="server-error">{{ serverError }}</div>
        <button type="submit" class="btn btn--primary btn--full" :disabled="loading">
          {{ loading ? 'Регистрация...' : 'Зарегистрироваться' }}
        </button>
      </form>
      <p class="register-footer">
        Уже есть аккаунт?
        <router-link to="/login">Войти</router-link>
      </p>
    </div>
  </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { registerUser } from '../../../logic/actions/index.js'
import { REGISTER_ROLES } from '../../../logic/constants/index.js'

const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const form = reactive({
  username: '',
  full_name: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'student',
})
const errors = reactive({
  username: '',
  full_name: '',
  email: '',
  password: '',
  confirmPassword: '',
})
const serverError = ref('')
const loading = ref(false)

function validate() {
  Object.keys(errors).forEach(k => errors[k] = '')
  let valid = true

  if (!form.username.trim()) {
    errors.username = 'Обязательное поле'
    valid = false
  } else if (form.username.trim().length < 3) {
    errors.username = 'Не менее 3 символов'
    valid = false
  }

  if (!form.full_name.trim()) {
    errors.full_name = 'Обязательное поле'
    valid = false
  }

  if (!form.email.trim()) {
    errors.email = 'Обязательное поле'
    valid = false
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = 'Некорректный email'
    valid = false
  }

  if (!form.password) {
    errors.password = 'Обязательное поле'
    valid = false
  } else if (form.password.length < 8) {
    errors.password = 'Не менее 8 символов'
    valid = false
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = 'Обязательное поле'
    valid = false
  } else if (form.password !== form.confirmPassword) {
    errors.confirmPassword = 'Пароли не совпадают'
    valid = false
  }

  return valid
}

async function handleSubmit() {
  serverError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    await registerUser({
      username: form.username.trim(),
      fullName: form.full_name.trim(),
      email: form.email.trim(),
      password: form.password,
      role: form.role,
    })
    router.push('/')
  } catch (err) {
    serverError.value = err.message || 'Ошибка сервера'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
.register-card {
  width: 100%;
  max-width: 400px;
  padding: var(--spacing-8);
  background: var(--color-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-gray-200);
}
.register-title {
  text-align: center;
  margin-bottom: var(--spacing-6);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary);
}
.register-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}
.register-footer {
  text-align: center;
  margin-top: var(--spacing-4);
  font-size: 13px;
  color: var(--color-gray-600);
}
</style>
