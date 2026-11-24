<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="student-settings-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Настройки ученика</h1>
          <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
        </div>
        <p class="page-desc">Параметры ученика</p>
      </div>
      <StudentSettingsTour v-if="showTour" @close="showTour = false" />

      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-if="loadErr" class="fmsg fmsg--err load-err">{{ loadErr }}</div>

      <template v-else>
        <section class="card">
          <h2 class="card-title">Основное</h2>
          <div class="form-grid">
            <label class="fl">Статус
              <select v-model="form.status">
                <option v-for="st in STUDENT_STATUSES" :key="st.value" :value="st.value">{{ st.label }}</option>
              </select>
            </label>
            <label class="fl">Часовой пояс
              <select v-model="form.timezone_offset">
                <option v-for="tz in TIMEZONES" :key="tz.value" :value="tz.value">{{ tz.label }}</option>
              </select>
            </label>
          </div>
          <label class="fl">Вид расписания
            <select v-model="form.schedule_view">
              <option v-for="st in SCHEDULE_TYPES" :key="st.value" :value="st.value">{{ st.label }}</option>
            </select>
          </label>
          <div v-if="form.status !== 'ACTIVE'" class="pick-empty">Неактивный статус блокирует самозапись на уроки</div>
          <label class="consent-row">
            <input v-model="form.require_link_consent" type="checkbox" />
            <span>Добавлять меня в связи только с моего согласия</span>
          </label>
          <p class="field-hint">
            Если включено, репетитор, узнавший ваш личный код, сможет только отправить заявку — связь появится после вашего подтверждения.
          </p>
        </section>

        <section class="card">
          <h2 class="card-title">Внешний вид расписания</h2>
          <div class="frow">
            <label class="fl">Отображать время от
              <input v-model="form.display_time_from" type="time" />
            </label>
            <label class="fl">до
              <input v-model="form.display_time_to" type="time" />
            </label>
          </div>
        </section>

        <div class="save-bar">
          <div v-if="saveMsg" class="fmsg fmsg--ok">{{ saveMsg }}</div>
          <div v-if="saveErr" class="fmsg fmsg--err">{{ saveErr }}</div>
          <button type="button" class="btn btn--gry" @click="handleReset" :disabled="saving">
            Сбросить
          </button>
          <button type="button" class="btn btn--pri" @click="handleSave" :disabled="saving">
            {{ saving ? '...' : 'Сохранить' }}
          </button>
        </div>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import StudentSettingsTour from './StudentSettingsTour.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { loadStudentProfile, saveStudentSettings } from '../../../logic/actions/index.js'
import { logInfo, logError } from '../../../logic/logger/index.js'
import { TIMEZONES, SCHEDULE_TYPES, STUDENT_STATUSES } from '../../../logic/constants/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const showTour = ref(false)

const loading = ref(true)
const saving = ref(false)
const saveMsg = ref('')
const saveErr = ref('')
const loadErr = ref('')

const defaultForm = () => ({
  status: 'ACTIVE',
  timezone_offset: 0,
  schedule_view: 'INFORMATIVE',
  display_time_from: '00:00',
  display_time_to: '23:59',
  require_link_consent: true,
})

const form = reactive(defaultForm())

function applyProfile(data) {
  Object.assign(form, {
    status: data.status ?? 'ACTIVE',
    timezone_offset: data.timezone_offset ?? 0,
    schedule_view: data.schedule_view ?? 'INFORMATIVE',
    display_time_from: data.display_time_from ?? '00:00',
    display_time_to: data.display_time_to ?? '23:59',
    require_link_consent: data.require_link_consent !== false,
  })
}

async function handleSave() {
  saveMsg.value = ''
  saveErr.value = ''
  saving.value = true
  try {
    const data = await saveStudentSettings({
      status: form.status,
      timezone_offset: form.timezone_offset,
      schedule_view: form.schedule_view,
      display_time_from: form.display_time_from,
      display_time_to: form.display_time_to,
      require_link_consent: form.require_link_consent,
    })
    applyProfile(data)
    saveMsg.value = 'Настройки сохранены'
    logInfo('student-settings', 'save:ok')
    setTimeout(() => saveMsg.value = '', 3000)
  } catch (e) {
    if (e.status) {
      saveErr.value = e.message || 'Ошибка сохранения'
      logError('student-settings', 'save:fail', { status: e.status, error: e.payload?.error })
    } else {
      saveErr.value = 'Сеть'
      logError('student-settings', 'save:networkError', { error: e.message })
    }
  } finally { saving.value = false }
}

async function handleReset() {
  if (!confirm('Сбросить настройки к значениям по умолчанию?')) return
  saveMsg.value = ''
  saveErr.value = ''
  saving.value = true
  try {
    const data = await saveStudentSettings({
      status: 'ACTIVE',
      timezone_offset: 0,
      schedule_view: 'INFORMATIVE',
      display_time_from: '00:00',
      display_time_to: '23:59',
    })
    applyProfile(data)
    saveMsg.value = 'Настройки сброшены'
    logInfo('student-settings', 'reset:ok')
    setTimeout(() => saveMsg.value = '', 3000)
  } catch (e) {
    if (e.status) {
      saveErr.value = e.message || 'Ошибка сброса'
      logError('student-settings', 'reset:fail', { status: e.status, error: e.payload?.error })
    } else {
      saveErr.value = 'Сеть'
      logError('student-settings', 'reset:networkError', { error: e.message })
    }
  } finally { saving.value = false }
}

onMounted(async () => {
  logInfo('student-settings', 'mounted:loading')
  loadErr.value = ''
  try {
    const data = await loadStudentProfile()
    applyProfile(data)
    logInfo('student-settings', 'mounted:profileLoaded')
  } catch (e) {
    loadErr.value = e.status ? 'Не удалось загрузить настройки' : 'Сеть'
    logError('student-settings', 'mounted:error', { error: e.message })
  } finally { loading.value = false }
})
</script>

<style scoped>
.consent-row { display: flex; gap: 8px; align-items: center; margin-top: 12px; font-size: 14px; cursor: pointer; }
.field-hint { margin: 6px 0 0; color: var(--muted, var(--color-gray-600)); font-size: 13px; line-height: 1.45; }
.student-settings-page { display: flex; flex-direction: column; }
.load-err { margin-bottom: 12px; }

.card {
  background: var(--surface); border-radius: 12px; border: 1px solid var(--color-gray-200);
  padding: 20px; display: flex; flex-direction: column; gap: 14px; margin-bottom: 16px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin: 0; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* Save */
.save-bar { display: flex; align-items: center; gap: 12px; justify-content: flex-end; padding: 8px 0; }

.card { padding: 24px; }
@media (max-width: 700px) { .form-grid { grid-template-columns: minmax(0, 1fr); } .card { padding: 16px; } }
</style>
