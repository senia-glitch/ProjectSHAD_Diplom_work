<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="admin-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Управление пользователями</h1>
          <div class="page-actions">
            <router-link to="/admin/logs" class="btn btn--gry btn--sm">Журнал</router-link>
            <router-link to="/admin/system" class="btn btn--gry btn--sm">Система</router-link>
          </div>
        </div>
        <p class="page-desc">Пользователи системы: данные, роли, табельные номера</p>
      </div>

      <div class="filter-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="content-grid">
        <div class="table-panel">
          <div class="table-wrap">
            <table class="users-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Логин</th>
                  <th>ФИО</th>
                  <th>Email</th>
                  <th>Роль</th>
                  <th>Таб. номер</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="u in filteredUsers"
                  :key="u.user_id"
                  :class="{ active: selected?.user_id === u.user_id }"
                  @click="selectUser(u)"
                >
                  <td class="col-id">{{ u.user_id }}</td>
                  <td class="col-login">{{ u.username }}</td>
                  <td>{{ u.full_name }}</td>
                  <td>{{ u.email }}</td>
                  <td>
                    <span class="role-badge" :class="'role-' + u.role_name">{{ roleLabel(u.role_name) }}</span>
                  </td>
                  <td>{{ u.personal_number }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!loading && !filteredUsers.length && !listError" class="empty">Нет пользователей</div>
            <div v-if="listError" class="empty empty--err">{{ listError }}</div>
            <div v-if="loading" class="empty">Загрузка...</div>
          </div>
        </div>

        <div class="detail-panel" v-if="selected && !loadingDetail">
          <h2 class="detail-title">{{ form.username }}</h2>
          <span class="role-badge" :class="'role-' + selected.role_name">{{ roleLabel(selected.role_name) }}</span>

          <form class="edit-form" @submit.prevent="handleSave" novalidate>
            <div class="form-group" :class="{ 'has-error': errors.full_name }">
              <label>ФИО</label>
              <input v-model="form.full_name" type="text" :class="{ error: errors.full_name }" />
              <span v-if="errors.full_name" class="field-error">{{ errors.full_name }}</span>
            </div>

            <div class="form-group" :class="{ 'has-error': errors.email }">
              <label>Email</label>
              <input v-model="form.email" type="email" :class="{ error: errors.email }" />
              <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
            </div>

            <div class="form-group" :class="{ 'has-error': errors.gender }">
              <label>Пол</label>
              <select v-model="form.gender" :class="{ error: errors.gender }">
                <option v-for="g in GENDERS" :key="g.value" :value="g.value">{{ g.label }}</option>
              </select>
              <span v-if="errors.gender" class="field-error">{{ errors.gender }}</span>
            </div>

            <div class="form-group" :class="{ 'has-error': errors.username }">
              <label>Логин</label>
              <input v-model="form.username" type="text" :class="{ error: errors.username }" />
              <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
            </div>

            <div class="form-group" :class="{ 'has-error': errors.personal_number }">
              <label>Табельный номер</label>
              <input v-model="form.personal_number" type="text" :class="{ error: errors.personal_number }" />
              <span v-if="errors.personal_number" class="field-error">{{ errors.personal_number }}</span>
            </div>

            <div class="form-group" :class="{ 'has-error': errors.additional_info }">
              <label>Доп. информация</label>
              <textarea v-model="form.additional_info" rows="3" :class="{ error: errors.additional_info }"></textarea>
              <span v-if="errors.additional_info" class="field-error">{{ errors.additional_info }}</span>
            </div>

            <div v-if="serverError" class="server-error">{{ serverError }}</div>
            <div v-if="successMsg" class="server-success">{{ successMsg }}</div>

            <button type="submit" class="btn btn--primary" :disabled="saving">
              {{ saving ? 'Сохранение...' : 'Сохранить' }}
            </button>
          </form>
        </div>

        <div class="detail-panel detail-panel--empty" v-else-if="!selected && !loadingDetail">
          <p>Выберите пользователя</p>
        </div>

        <div class="detail-panel detail-panel--empty" v-else>
          <p>Загрузка...</p>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { loadAdminUsers, loadAdminUser, saveAdminUser } from '../../../logic/actions/index.js'
import { logError } from '../../../logic/logger/index.js'
import { useAdminStore } from '../../../logic/store/index.js'
import { roleLabel, ROLE_LABELS, GENDERS } from '../../../logic/constants/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const adminStore = useAdminStore()
const users = computed(() => adminStore.users)
const selected = ref(null)
const activeTab = ref('all')
const loading = ref(false)
const loadingDetail = ref(false)
const saving = ref(false)
const serverError = ref('')
const successMsg = ref('')
const listError = ref('')

const form = reactive({
  full_name: '',
  email: '',
  gender: 'male',
  username: '',
  personal_number: '',
  additional_info: '',
})
const errors = reactive({
  full_name: '',
  email: '',
  gender: '',
  username: '',
  personal_number: '',
  additional_info: '',
})

const tabs = [
  { key: 'all', label: 'Все' },
  ...Object.entries(ROLE_LABELS).map(([key, label]) => ({ key, label: `${label}ы` })),
]

const filteredUsers = computed(() => {
  if (activeTab.value === 'all') return users.value
  return users.value.filter((u) => u.role_name === activeTab.value)
})

function clearErrors() {
  for (const k in errors) errors[k] = ''
}

async function fetchUsers() {
  loading.value = true
  listError.value = ''
  try {
    await loadAdminUsers({ limit: 100, offset: 0 })
  } catch (e) {
    listError.value = e.status ? 'Не удалось загрузить пользователей' : 'Сеть'
    logError('admin', 'fetchUsers:error', { error: e.message })
  }
  loading.value = false
}

// Порядковый номер запроса деталей: последний клик заменяет
// «последний запрос», устаревший ответ не меняет форму.
let detailSeq = 0

async function selectUser(user) {
  if (selected.value?.user_id === user.user_id) return
  loadingDetail.value = true
  selected.value = null
  serverError.value = ''
  successMsg.value = ''
  clearErrors()
  const my = ++detailSeq
  try {
    const data = await loadAdminUser(user.user_id)
    if (my !== detailSeq) return
    selected.value = data
    form.full_name = data.full_name || ''
    form.email = data.email || ''
    form.gender = data.gender || 'male'
    form.username = data.username || ''
    form.personal_number = data.personal_number || ''
    form.additional_info = data.additional_info || ''
  } catch (e) {
    if (my === detailSeq) {
      serverError.value = e.status ? 'Не удалось загрузить данные пользователя' : 'Сеть'
    }
    logError('admin', 'selectUser:error', { error: e.message })
  } finally {
    if (my === detailSeq) loadingDetail.value = false
  }
}

function validate() {
  clearErrors()
  let valid = true

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

  if (!form.username.trim()) {
    errors.username = 'Обязательное поле'
    valid = false
  } else if (form.username.trim().length < 3) {
    errors.username = 'Не менее 3 символов'
    valid = false
  }

  return valid
}

async function handleSave() {
  serverError.value = ''
  successMsg.value = ''
  if (!validate()) return

  saving.value = true
  try {
    const updated = await saveAdminUser(selected.value.user_id, {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      gender: form.gender,
      username: form.username.trim(),
      personal_number: form.personal_number.trim(),
      additional_info: form.additional_info.trim(),
    })
    successMsg.value = 'Данные сохранены'
    selected.value = { ...selected.value, ...updated }
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (e) {
    serverError.value = e.status ? e.message || 'Ошибка сохранения' : 'Ошибка сети'
  }
  saving.value = false
}

onMounted(fetchUsers)
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; }
.empty--err { color: var(--color-danger); }

.filter-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.tab {
  padding: 8px 16px; border-radius: 6px; border: 1px solid var(--color-gray-200); background: white;
  font-size: 13px; font-weight: 500; color: var(--color-gray-700); cursor: pointer; transition: all 150ms;
}
.tab:hover { background: var(--color-gray-50); }
.tab.active { background: var(--color-accent); color: white; border-color: var(--color-accent); }

.content-grid { display: grid; grid-template-columns: 1fr 380px; gap: 16px; min-height: 500px; }

.table-panel { background: white; border-radius: 12px; border: 1px solid var(--color-gray-200); overflow: hidden; }
.table-wrap { overflow-x: auto; }
.users-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.users-table th {
  text-align: left; padding: 12px 16px; font-weight: 600; color: var(--color-gray-700);
  border-bottom: 2px solid var(--color-gray-200); white-space: nowrap; background: var(--color-gray-50);
}
.users-table td { padding: 10px 16px; border-bottom: 1px solid var(--color-gray-100); }
.users-table tr { cursor: pointer; transition: background 150ms; }
.users-table tbody tr:hover { background: var(--color-gray-50); }
.users-table tr.active { background: rgba(58,122,189,0.1); }
.col-id { color: var(--color-gray-600); font-size: 13px; }
.col-login { font-weight: 500; color: var(--color-primary); }

.role-badge {
  display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600;
}
.role-student { background: var(--role-student-bg); color: var(--role-student-text); }
.role-tutor { background: var(--role-tutor-bg); color: var(--role-tutor-text); }
.role-admin { background: var(--role-admin-bg); color: var(--role-admin-text); }

.detail-panel {
  background: white; border-radius: 12px; border: 1px solid var(--color-gray-200); padding: 24px;
  display: flex; flex-direction: column; gap: 16px; overflow-y: auto;
}
.detail-panel--empty { display: flex; align-items: center; justify-content: center; color: var(--color-gray-500); }
.detail-title { font-size: 20px; font-weight: 600; margin: 0; }

.edit-form { display: flex; flex-direction: column; gap: 14px; }
</style>
