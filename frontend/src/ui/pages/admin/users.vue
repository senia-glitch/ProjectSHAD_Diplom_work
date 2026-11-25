<template>
  <AdminShell title="Пользователи" lead="Данные, роли, блокировка, сброс пароля и удаление учётных записей.">
    <div class="row users-filters">
      <div class="filter-tabs" role="tablist" aria-label="Роль">
        <button v-for="tab in tabs" :key="tab.key" type="button" class="chip tab-chip" :class="{ on: activeTab === tab.key }" role="tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">
          {{ tab.label }} <small class="muted">{{ tabCount(tab.key) }}</small>
        </button>
      </div>
      <input v-model="query" type="search" class="grow" placeholder="Логин, ФИО, почта, код" aria-label="Поиск пользователя" />
    </div>

    <div class="users-grid">
      <div class="table-wrap">
        <table class="users-table">
          <thead><tr><th>ID</th><th>Логин</th><th>ФИО</th><th>Почта</th><th>Роль</th><th>Статус</th></tr></thead>
          <tbody>
            <tr
              v-for="u in filteredUsers"
              :key="u.user_id"
              :class="{ active: selected?.user_id === u.user_id }"
              tabindex="0"
              @click="selectUser(u)"
              @keydown.enter="selectUser(u)"
            >
              <td class="muted">{{ u.user_id }}</td>
              <td><strong>{{ u.username }}</strong></td>
              <td>{{ u.full_name }}</td>
              <td class="small">{{ u.email }}</td>
              <td><span class="pill" :class="rolePill(u.role_name)">{{ roleLabel(u.role_name) }}</span></td>
              <td><span v-if="u.blocked_at" class="pill pill-red">заблокирован</span><span v-else class="pill pill-green">активен</span></td>
            </tr>
          </tbody>
        </table>
        <p v-if="loading" class="muted pad">Загрузка…</p>
        <p v-else-if="listError" class="notice error">{{ listError }}</p>
        <p v-else-if="!filteredUsers.length" class="muted pad">Нет пользователей</p>
      </div>

      <aside class="panel detail">
        <p v-if="loadingDetail" class="muted">Загрузка…</p>
        <p v-else-if="!selected" class="muted">Выберите пользователя в таблице.</p>
        <template v-else>
          <div>
            <h2 class="detail-title">{{ selected.username }}</h2>
            <div class="stat-row">
              <span class="pill" :class="rolePill(selected.role_name)">{{ roleLabel(selected.role_name) }}</span>
              <span v-if="selected.blocked_at" class="pill pill-red">заблокирован {{ formatLocalDateTime(selected.blocked_at) }}</span>
            </div>
            <p v-if="selected.blocked_at && selected.block_reason" class="muted small">Причина: {{ selected.block_reason }}</p>
          </div>

          <form class="stack-sm" novalidate @submit.prevent="handleSave">
            <label>ФИО <input v-model="form.full_name" type="text" :aria-invalid="!!errors.full_name" /></label>
            <span v-if="errors.full_name" class="error-text">{{ errors.full_name }}</span>
            <label>Почта <input v-model="form.email" type="text" inputmode="email" :aria-invalid="!!errors.email" /></label>
            <span v-if="errors.email" class="error-text">{{ errors.email }}</span>
            <label>Логин <input v-model="form.username" type="text" :aria-invalid="!!errors.username" /></label>
            <span v-if="errors.username" class="error-text">{{ errors.username }}</span>
            <label>Пол
              <select v-model="form.gender">
                <option v-for="g in GENDERS" :key="g.value" :value="g.value">{{ g.label }}</option>
              </select>
            </label>
            <label>Личный код <input v-model="form.personal_number" type="text" /></label>
            <label>О себе <textarea v-model="form.additional_info" rows="3"></textarea></label>
            <div v-if="serverError" class="notice error" role="alert">{{ serverError }}</div>
            <div v-if="successMsg" class="notice ok">{{ successMsg }}</div>
            <div><button type="submit" class="btn primary" :disabled="saving">{{ saving ? 'Сохранение…' : 'Сохранить' }}</button></div>
          </form>

          <div v-if="!isSelf" class="stack-sm actions-block">
            <div class="admin-title">Действия</div>
            <div v-if="tempPassword" class="notice ok stack-sm">
              <span>Временный пароль (показан один раз, передайте пользователю):</span>
              <code class="mono temp">{{ tempPassword }}</code>
            </div>
            <div class="row action-row">
              <button v-if="selected.blocked_at" type="button" class="btn ghost" :disabled="busy" @click="doUnblock">Разблокировать</button>
              <button v-else type="button" class="btn amber" :disabled="busy" @click="doBlock">Заблокировать</button>
              <button v-if="selected.role_name !== 'admin'" type="button" class="btn ghost" :disabled="busy" @click="doReset">Сбросить пароль</button>
              <button type="button" class="btn danger" :disabled="busy" @click="doDelete">Удалить</button>
            </div>
          </div>
          <p v-else class="muted small">Это ваша учётная запись: блокировка и удаление недоступны.</p>
        </template>
      </aside>
    </div>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AdminShell from './AdminShell.vue'
import { useUser } from '../../composables/index.js'
import {
  blockUser, loadAdminUser, loadAdminUsers, removeAdminUser, resetUserPassword, saveAdminUser, unblockUser,
} from '../../../logic/actions/index.js'
import { logError } from '../../../logic/logger/index.js'
import { useAdminStore } from '../../../logic/store/index.js'
import { roleLabel, ROLE_LABELS, GENDERS } from '../../../logic/constants/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'
import { formatLocalDateTime } from './adminFormat.js'

const { userId } = useUser()
const adminStore = useAdminStore()
const users = computed(() => adminStore.users)
const selected = ref(null)
const activeTab = ref('all')
const query = ref('')
const loading = ref(false)
const loadingDetail = ref(false)
const saving = ref(false)
const busy = ref(false)
const serverError = ref('')
const successMsg = ref('')
const listError = ref('')
const tempPassword = ref('')

const form = reactive({ full_name: '', email: '', gender: 'male', username: '', personal_number: '', additional_info: '' })
const errors = reactive({ full_name: '', email: '', username: '' })

const tabs = [
  { key: 'all', label: 'Все' },
  ...Object.entries(ROLE_LABELS).map(([key, label]) => ({ key, label: `${label}ы` })),
  { key: 'blocked', label: 'Заблокированные' },
]
const isSelf = computed(() => selected.value && String(selected.value.user_id) === String(userId.value))
const rolePill = (r) => (r === 'admin' ? 'pill-violet' : r === 'tutor' ? 'pill-blue' : 'pill-gray')

function matchesTab(u, key) {
  if (key === 'all') return true
  if (key === 'blocked') return !!u.blocked_at
  return u.role_name === key
}
const tabCount = (key) => users.value.filter((u) => matchesTab(u, key)).length
const filteredUsers = computed(() => {
  const q = query.value.trim().toLowerCase()
  return users.value.filter((u) => matchesTab(u, activeTab.value) && (!q || [u.username, u.full_name, u.email, u.personal_number, String(u.user_id)]
    .some((v) => (v || '').toLowerCase().includes(q))))
})

async function fetchUsers() {
  loading.value = true
  listError.value = ''
  try {
    await loadAdminUsers({ limit: 1000, offset: 0 })
  } catch (e) {
    listError.value = e.message || 'Не удалось загрузить пользователей'
    logError('admin', 'fetchUsers:error', { error: e.message })
  }
  loading.value = false
}

let detailSeq = 0
async function selectUser(user) {
  if (selected.value?.user_id === user.user_id) return
  loadingDetail.value = true
  selected.value = null
  serverError.value = ''
  successMsg.value = ''
  tempPassword.value = ''
  for (const k in errors) errors[k] = ''
  const my = ++detailSeq
  try {
    const data = await loadAdminUser(user.user_id)
    if (my !== detailSeq) return
    selected.value = data
    Object.assign(form, {
      full_name: data.full_name || '', email: data.email || '', gender: data.gender || 'male',
      username: data.username || '', personal_number: data.personal_number || '', additional_info: data.additional_info || '',
    })
  } catch (e) {
    if (my === detailSeq) toast(e.message || 'Не удалось загрузить пользователя', 'error')
  } finally {
    if (my === detailSeq) loadingDetail.value = false
  }
}

function validate() {
  for (const k in errors) errors[k] = ''
  if (!form.full_name.trim()) errors.full_name = 'Обязательное поле'
  if (!form.email.trim()) errors.email = 'Обязательное поле'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errors.email = 'Некорректная почта'
  if (form.username.trim().length < 3) errors.username = 'Не менее 3 символов'
  return !errors.full_name && !errors.email && !errors.username
}

async function handleSave() {
  serverError.value = ''
  successMsg.value = ''
  if (!validate()) return
  saving.value = true
  try {
    const updated = await saveAdminUser(selected.value.user_id, {
      full_name: form.full_name.trim(), email: form.email.trim(), gender: form.gender, username: form.username.trim(),
      personal_number: form.personal_number.trim(), additional_info: form.additional_info.trim(),
    })
    selected.value = { ...selected.value, ...updated }
    successMsg.value = 'Данные сохранены'
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (e) {
    serverError.value = e.message || 'Ошибка сохранения'
  }
  saving.value = false
}

async function withBusy(fn) {
  tempPassword.value = ''
  busy.value = true
  try { await fn() } catch (e) { toast(e.message || 'Действие не выполнено', 'error') } finally { busy.value = false }
}

async function doBlock() {
  const u = selected.value
  const reason = await askConfirm(`Заблокировать ${u.username}?`, 'Пользователь сразу потеряет доступ: текущие сессии завершатся, войти снова он не сможет.', {
    input: { placeholder: 'Причина (видна только в админ-панели)', validate: (v) => (v ? '' : 'Укажите причину') },
    okText: 'Заблокировать', danger: true,
  })
  if (!reason) return
  await withBusy(async () => {
    await blockUser(u.user_id, reason)
    selected.value = { ...u, blocked_at: new Date().toISOString(), block_reason: reason }
    toast('Пользователь заблокирован', 'ok')
  })
}

async function doUnblock() {
  const u = selected.value
  await withBusy(async () => {
    await unblockUser(u.user_id)
    selected.value = { ...u, blocked_at: null, block_reason: null }
    toast('Пользователь разблокирован', 'ok')
  })
}

async function doReset() {
  const u = selected.value
  const ok = await askConfirm(`Сбросить пароль ${u.username}?`, 'Будет создан временный пароль, текущие сессии пользователя завершатся.', { okText: 'Сбросить' })
  if (!ok) return
  await withBusy(async () => {
    tempPassword.value = (await resetUserPassword(u.user_id)).temporary_password || ''
  })
}

async function doDelete() {
  const u = selected.value
  const ok = await askConfirm(`Удалить ${u.username}?`, 'Учётная запись и все связанные данные (уроки, связи, записи блога) будут удалены безвозвратно.', { okText: 'Удалить навсегда', danger: true })
  if (!ok) return
  await withBusy(async () => {
    await removeAdminUser(u.user_id)
    selected.value = null
    toast('Пользователь удалён', 'ok')
  })
}

onMounted(() => {
  document.title = 'Пользователи · SHAD'
  fetchUsers()
})
</script>

<style scoped>
.users-filters { gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }
.users-filters input { min-width: 220px; }
.users-grid > .table-wrap { overflow-x: auto; }
.users-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
.tab-chip { cursor: pointer; font-size: 13px; touch-action: auto; }
.users-table tbody tr { cursor: pointer; }
.users-table tbody tr:hover { background: var(--surface-2); }
.users-table tbody tr.active { background: var(--accent-soft); }
.users-table td { white-space: nowrap; }
.detail { display: grid; gap: 16px; position: sticky; top: calc(var(--header-h, 64px) + 16px); }
.detail-title { font-size: 20px; margin: 0 0 8px; }
.actions-block { border-top: 1px solid var(--line); padding-top: 14px; }
.action-row { gap: 8px; flex-wrap: wrap; }
.temp { font-size: 15px; user-select: all; }
.pad { padding: 14px; margin: 0; }
.admin-title { padding: 0; }
@media (max-width: 1050px) { .users-grid { grid-template-columns: minmax(0, 1fr); } .detail { position: static; } }
</style>
