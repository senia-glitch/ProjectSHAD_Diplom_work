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
          <UserAvatar class="avatar-photo" :src="form.avatar_url.trim()" :name="user.full_name || user.username" :size="72" />
          <div>
            <h2 class="profile-name">{{ user.full_name || user.username }}</h2>
            <p class="profile-role">{{ { tutor: 'Репетитор', student: 'Ученик', admin: 'Администратор' }[user.role] || user.role }}</p>
            <p v-if="user.personal_number" class="profile-code">Ваш личный код: <span class="mono">{{ user.personal_number }}</span></p>
          </div>
        </div>
      </div>
      <div v-if="user" class="profile-card">
        <h3 class="card-title">Личные данные</h3>
        <form class="profile-form" @submit.prevent="handleUpdate" novalidate>
          <div class="form-group" :class="{ 'has-error': errors.full_name }">
            <label for="profile-name">ФИО</label>
            <input
              id="profile-name"
              v-model="form.full_name"
              type="text"
              autocomplete="name"
              :aria-invalid="!!errors.full_name"
              :aria-describedby="errors.full_name ? 'profile-name-error' : undefined"
              :class="{ error: errors.full_name }"
            />
            <span v-if="errors.full_name" id="profile-name-error" class="field-error">{{ errors.full_name }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': errors.email }">
            <label for="profile-email">Почта</label>
            <input
              id="profile-email"
              v-model="form.email"
              type="email"
              autocomplete="email"
              :class="{ error: errors.email }"
            />
            <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': errors.avatar_url }">
            <label for="profile-avatar">Фото профиля — ссылка на изображение</label>
            <div class="avatar-row">
              <input
                id="profile-avatar"
                v-model="form.avatar_url"
                type="url"
                inputmode="url"
                placeholder="https://…/photo.jpg"
                :aria-invalid="!!errors.avatar_url"
                aria-describedby="profile-avatar-hint"
                :class="{ error: errors.avatar_url }"
              />
              <button v-if="form.avatar_url" type="button" class="btn btn--gry btn--sm" @click="form.avatar_url = ''">Убрать</button>
            </div>
            <span v-if="errors.avatar_url" class="field-error">{{ errors.avatar_url }}</span>
            <span v-else id="profile-avatar-hint" class="field-hint">Вставьте прямую ссылку на картинку (https://…). Фото видно сразу слева; сохраните, чтобы его увидели другие.</span>
          </div>
          <div v-if="serverError" class="server-error" role="alert">{{ serverError }}</div>
          <div v-if="successMsg" class="server-success" role="status">{{ successMsg }}</div>
          <button type="submit" class="btn btn--primary" :disabled="loading">
            {{ loading ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </form>
      </div>
      <div v-if="user" class="profile-card profile-card--wide">
        <h3 class="card-title">Вид интерфейса</h3>
        <fieldset class="nav-modes">
          <legend class="sr-only">Вид интерфейса</legend>
          <label v-for="m in NAV_MODES" :key="m.value" class="nav-mode" :class="{ on: navMode === m.value }">
            <input type="radio" name="nav-mode" :value="m.value" :checked="navMode === m.value" @change="changeNavMode(m.value)" />
            <span><strong>{{ m.label }}</strong><small>{{ m.hint }}</small></span>
          </label>
        </fieldset>
        <p class="field-hint">Меню слева показывается на экранах от 1100 px; на телефоне меню всегда компактное.</p>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import ProfileTour from './ProfileTour.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { UserAvatar } from '../../components/index.js'
import { NAV_MODES, scheduleTypeFromNavMode, useNavMode } from '../../composables/index.js'
import { loadMyProfile, saveMyProfile, saveTutorSettings } from '../../../logic/actions/index.js'
import { useAuthStore } from '../../../logic/store/index.js'
import { logError } from '../../../logic/logger/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const showTour = ref(false)
const { navMode, setNavMode } = useNavMode()

// Вид меню применяется сразу; репетитору он сохраняется и в настройках (виден на всех устройствах).
async function changeNavMode(value) {
  setNavMode(value)
  if (role.value !== 'tutor') return
  try {
    await saveTutorSettings({ schedule_type: scheduleTypeFromNavMode(value) })
  } catch (e) {
    logError('profile', 'nav-mode:error', { error: e.message })
  }
}

const user = ref(null)
const form = reactive({ full_name: '', email: '', avatar_url: '' })
const errors = reactive({ full_name: '', email: '', avatar_url: '' })
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
    form.avatar_url = data.avatar_url || ''
  } catch (e) {
    loadError.value = e.status ? 'Не удалось загрузить профиль' : 'Сеть'
    logError('profile', 'mounted:error', { error: e.message })
  }
})

function validate() {
  errors.full_name = ''
  errors.email = ''
  errors.avatar_url = ''
  let valid = true
  const avatar = form.avatar_url.trim()
  if (avatar && (!/^https?:\/\/\S+$/i.test(avatar) || avatar.length > 500)) {
    errors.avatar_url = 'Нужна ссылка вида https://… без пробелов'
    valid = false
  }

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
    const data = await saveMyProfile({ full_name: form.full_name.trim(), email: form.email.trim(), avatar_url: form.avatar_url.trim() })
    successMsg.value = 'Данные сохранены'
    user.value = { ...user.value, ...data }
    // Шапка сайта читает имя из authStore.user — синхронизируем её
    // с сохранённым профилем, иначе имя в шапке останется старым.
    useAuthStore().setUser({ ...useAuthStore().user, ...data })
    form.full_name = data.full_name || user.value.full_name
    form.email = data.email || user.value.email
    form.avatar_url = data.avatar_url || ''
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
.profile-card { background: var(--surface); border-radius: 12px; padding: 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid var(--color-gray-200); margin-bottom: 16px; }
.profile-card:last-child { margin-bottom: 0; }
.profile-header { display: flex; align-items: center; gap: 16px; }
.avatar { width: 64px; height: 64px; border-radius: 50%; background: var(--accent); display: flex; align-items: center; justify-content: center; color: var(--on-accent); font-size: 24px; font-weight: 700; }
.profile-name { font-size: 20px; font-weight: 600; }
.profile-role { font-size: 14px; color: var(--color-gray-600); }
.profile-code { font-size: 13px; color: var(--color-gray-700); margin: 4px 0 0; }
.profile-code .mono { font-family: monospace; font-size: 13px; }
.card-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.profile-form { display: flex; flex-direction: column; gap: 16px; }
.profile-form .form-group input { width: 100%; }
.profile-form .btn { align-self: flex-start; }
.loading-text { text-align: center; padding: 60px; color: var(--color-gray-600); }

.profile-page { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 24px; align-items: start; }
.profile-page > .page-header, .profile-page > .loading-text, .profile-page > .server-error { grid-column: 1 / -1; margin-bottom: 0; }
.profile-card { margin-bottom: 0; box-shadow: none; min-width: 0; }
.profile-header { flex-direction: column; align-items: flex-start; }
.avatar-photo { border-radius: 16px; }
.avatar-row { display: flex; gap: 8px; align-items: center; }
.avatar-row input { flex: 1; min-width: 0; }
.field-hint { font-size: 12px; color: var(--muted); }
.profile-card--wide { grid-column: 2; }
.nav-modes { border: 0; padding: 0; margin: 0 0 10px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.nav-mode { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px; cursor: pointer; }
.nav-mode.on { border-color: var(--accent); background: var(--accent-soft); }
.nav-mode input { margin-top: 3px; accent-color: var(--accent); }
.nav-mode span { display: grid; gap: 2px; }
.nav-mode small { color: var(--muted); font-size: 12.5px; line-height: 1.4; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
@media (max-width: 800px) { .profile-card--wide { grid-column: auto; } }
.profile-code { overflow-wrap: anywhere; line-height: 1.8; }
.profile-role { display: inline-block; margin-top: 8px; padding: 2px 8px; background: var(--accent-soft); color: var(--accent); border-radius: 6px; font-size: 12px; }
@media (max-width: 800px) { .profile-page { grid-template-columns: minmax(0, 1fr); gap: 16px; } .profile-header { flex-direction: row; align-items: center; } .avatar { flex-shrink: 0; } }
</style>
