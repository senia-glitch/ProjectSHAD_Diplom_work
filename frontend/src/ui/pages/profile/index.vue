<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="profile-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Профиль</h1>
          <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
        </div>
        <p class="page-desc">Личные данные аккаунта</p>
      </div>
      <ProfileTour v-if="showTour" @close="showTour = false" />
      <div v-if="!user && !loadError" class="loading-text">Загрузка...</div>
      <div v-if="loadError" class="server-error">{{ loadError }}</div>
      <div class="profile-card" v-if="user">
        <div class="profile-header">
          <div class="avatar"><span>{{ user.full_name?.charAt(0)?.toUpperCase() || user.username?.charAt(0)?.toUpperCase() || '?' }}</span></div>
          <div>
            <h2 class="profile-name">{{ user.full_name || user.username }}</h2>
            <p class="profile-role">{{ user.role }}</p>
            <p v-if="user.personal_number" class="profile-code">Ваш личный код: <span class="mono">{{ user.personal_number }}</span></p>
          </div>
        </div>
      </div>
      <div class="profile-card">
        <h3 class="card-title">Личные данные</h3>
        <form class="profile-form" @submit.prevent="handleUpdate" novalidate>
          <div class="form-group" :class="{ 'has-error': errors.full_name }">
            <label>ФИО</label>
            <input
              v-model="form.full_name"
              type="text"
              :class="{ error: errors.full_name }"
            />
            <span v-if="errors.full_name" class="field-error">{{ errors.full_name }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': errors.email }">
            <label>Email</label>
            <input
              v-model="form.email"
              type="email"
              autocomplete="email"
              :class="{ error: errors.email }"
            />
            <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
          </div>
          <div v-if="serverError" class="server-error">{{ serverError }}</div>
          <div v-if="successMsg" class="server-success">{{ successMsg }}</div>
          <button type="submit" class="btn btn--primary" :disabled="loading">
            {{ loading ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </form>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import ProfileTour from './ProfileTour.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { loadMyProfile, saveMyProfile } from '../../../logic/actions/index.js'
import { useAuthStore } from '../../../logic/store/index.js'
import { logError } from '../../../logic/logger/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const showTour = ref(false)

const user = ref(null)
const form = reactive({ full_name: '', email: '' })
const errors = reactive({ full_name: '', email: '' })
const loading = ref(false)
const serverError = ref('')
const successMsg = ref('')
const loadError = ref('')

onMounted(async () => {
  loadError.value = ''
  try {
    const data = await loadMyProfile()
    user.value = data
    form.full_name = data.full_name || ''
    form.email = data.email
  } catch (e) {
    loadError.value = e.status ? 'Не удалось загрузить профиль' : 'Сеть'
    logError('profile', 'mounted:error', { error: e.message })
  }
})

function validate() {
  errors.full_name = ''
  errors.email = ''
  let valid = true

  if (!form.full_name.trim()) {
    errors.full_name = 'Обязательное поле'
    valid = false
  } else if (form.full_name.trim().length < 2) {
    errors.full_name = 'Не менее 2 символов'
    valid = false
  }

  if (!form.email.trim()) {
    errors.email = 'Обязательное поле'
    valid = false
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = 'Некорректный email'
    valid = false
  }

  return valid
}

async function handleUpdate() {
  serverError.value = ''
  successMsg.value = ''
  if (!validate()) return

  loading.value = true
  try {
    const data = await saveMyProfile({ full_name: form.full_name.trim(), email: form.email.trim() })
    successMsg.value = 'Данные сохранены'
    user.value = { ...user.value, ...data }
    // Шапка сайта читает имя из authStore.user — синхронизируем её
    // с сохранённым профилем, иначе имя в шапке останется старым.
    useAuthStore().setUser({ ...useAuthStore().user, ...data })
    form.full_name = data.full_name || user.value.full_name
    form.email = data.email || user.value.email
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (e) {
    serverError.value = e.status ? e.message || 'Ошибка сохранения' : 'Ошибка сети'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-page { display: flex; flex-direction: column; }
.profile-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid var(--color-gray-200); margin-bottom: 16px; }
.profile-card:last-child { margin-bottom: 0; }
.profile-header { display: flex; align-items: center; gap: 16px; }
.avatar { width: 64px; height: 64px; border-radius: 50%; background: var(--color-primary); display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: 700; }
.profile-name { font-size: 20px; font-weight: 600; }
.profile-role { font-size: 14px; color: var(--color-gray-600); }
.profile-code { font-size: 13px; color: var(--color-gray-700); margin: 4px 0 0; }
.profile-code .mono { font-family: monospace; font-size: 13px; }
.card-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.profile-form { display: flex; flex-direction: column; gap: 16px; }
.profile-form .form-group input { width: 100%; }
.profile-form .btn { align-self: flex-start; }
.loading-text { text-align: center; padding: 60px; color: var(--color-gray-600); }
</style>
