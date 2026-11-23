<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="settings-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Настройки репетитора</h1>
          <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
        </div>
        <p class="page-desc">Управление параметрами репетитора</p>
      </div>
      <SettingsTour v-if="showTour" @close="showTour = false" />

      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-if="loadErr" class="fmsg fmsg--err load-err">{{ loadErr }}</div>

      <template v-else>
        <!-- === Административные === -->
        <section class="card">
          <h2 class="card-title">Административные</h2>
          <div class="form-grid">
            <label class="fl">Часовой пояс
              <select v-model="form.timezone_offset">
                <option v-for="tz in TIMEZONES" :key="tz.value" :value="tz.value">{{ tz.label }}</option>
              </select>
            </label>
            <label class="fl">Статус работы
              <select v-model="form.work_status">
                <option v-for="st in WORK_STATUSES" :key="st.value" :value="st.value">{{ st.label }}</option>
              </select>
            </label>
          </div>
        </section>

        <!-- === Внешний вид расписания === -->
        <section class="card">
          <h2 class="card-title">Внешний вид расписания</h2>
          <div class="form-grid">
            <label class="fl">Тип расписания
              <select v-model="form.schedule_type">
                <option v-for="st in SCHEDULE_TYPES" :key="st.value" :value="st.value">{{ st.label }}</option>
              </select>
            </label>
            <div class="frow">
              <label class="fl">Отображать время от
                <input v-model="form.display_time_from" type="time" />
              </label>
              <label class="fl">до
                <input v-model="form.display_time_to" type="time" />
              </label>
            </div>
          </div>
        </section>

        <!-- === Возможности учеников === -->
        <section class="card">
          <h2 class="card-title">Возможности учеников</h2>
          <div class="form-col">
            <div class="toggle-row">
              <span class="toggle-label">Самостоятельная запись учеников</span>
              <label class="toggle">
                <input type="checkbox" :checked="form.self_booking_mode === 'YES'" @change="toggleSelfBooking" />
                <span class="toggle-track"></span>
              </label>
              <span class="toggle-hint">{{ form.self_booking_mode === 'YES' ? 'Да (для всех)' : 'Нет' }}</span>
            </div>
            <div class="whitelist-section" :class="{ 'whitelist-section--disabled': form.self_booking_mode === 'YES' }">
              <div class="whitelist-head">
                <span class="whitelist-title">Всегда да для</span>
                <button type="button" class="icon-btn icon-btn--add" :disabled="form.self_booking_mode === 'YES'" @click="showStudentPicker = true">+</button>
              </div>
              <div v-if="!form.self_booking_whitelist?.length" class="part-empty">Нет учеников в белом списке</div>
              <div v-for="uid in form.self_booking_whitelist" :key="uid" class="part-chip">
                <span>{{ studentName(uid) }}</span>
                <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" :disabled="form.self_booking_mode === 'YES'" @click="removeFromWhitelist(uid)">−</button>
              </div>
            </div>
            <div class="frow">
              <label class="fl">Запись возможна за (часов)
                <input v-model.number="form.booking_lead_time_hours" type="number" min="0" max="168" />
              </label>
              <label class="fl">Отмена возможна за (часов)
                <input v-model.number="form.cancellation_lead_time_hours" type="number" min="0" max="168" />
              </label>
            </div>
          </div>
        </section>

        <!-- === Ссылки по умолчанию === -->
        <section class="card">
          <h2 class="card-title">Ссылки по умолчанию для новых учеников</h2>
          <div class="links-list">
            <div v-for="(link, i) in form.default_links" :key="i" class="link-row">
              <input v-model="link.alias" placeholder="Псевдоним" class="link-alias" />
              <input v-model="link.url" placeholder="https://..." class="link-url" :class="{ 'input-err': link._urlErr }" />
              <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" @click="removeLink(i)">−</button>
              <div v-if="link._urlErr" class="ferr">{{ link._urlErr }}</div>
            </div>
          </div>
          <button v-if="form.default_links.length < 10" type="button" class="icon-btn icon-btn--add" @click="addLink">+</button>
          <div v-if="form.default_links.length >= 10" class="pick-empty">Максимум 10 ссылок</div>
        </section>

        <!-- === Оплата новых учеников === -->
        <section class="card">
          <h2 class="card-title">Оплата новых учеников</h2>
          <div class="frow">
            <label class="fl">Стоимость времени
              <div class="input-with-suffix">
                <input v-model.number="form.hourly_rate" type="number" min="0" step="100" />
                <span class="suffix">руб/час</span>
              </div>
            </label>
            <label class="fl">Скидка
              <div class="input-with-suffix">
                <input v-model.number="form.discount" type="number" min="0" max="100" step="5" />
                <span class="suffix">%</span>
              </div>
            </label>
          </div>
          <div v-if="form.hourly_rate > 0 && form.discount > 0" class="final-price">
            <span class="final-price-label">Итого для ученика:</span>
            <span class="final-price-val">{{ finalPrice(form.hourly_rate, form.discount) }} руб/час</span>
            <span class="final-price-save">−{{ discountAmount(form.hourly_rate, form.discount) }} руб</span>
          </div>
        </section>

        <!-- === Save === -->
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

      <!-- Student picker modal -->
      <Teleport to="body">
        <div v-if="showStudentPicker" class="modal-overlay" @click.self="showStudentPicker = false">
          <div class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-student-picker-title">
            <h3 id="settings-student-picker-title" class="modal-title">Выберите ученика</h3>
            <div v-if="!students.length" class="modal-empty">Нет учеников</div>
            <div v-else class="modal-list">
              <button
                v-for="s in availableForWhitelist"
                :key="s.student_id"
                type="button"
                class="modal-item"
                @click="addToWhitelist(s.student_id)"
              >{{ s.full_name }}</button>
              <div v-if="!availableForWhitelist.length" class="modal-empty">Все ученики уже добавлены</div>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn btn--gry" @click="showStudentPicker = false">Отмена</button>
            </div>
          </div>
        </div>
      </Teleport>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import SettingsTour from './SettingsTour.vue'
import { useUser, useLogout, useEscapeKey } from '../../composables/index.js'
import { loadTutorProfile, loadTutorStudents, saveTutorSettings } from '../../../logic/actions/index.js'
import { logInfo, logError } from '../../../logic/logger/index.js'
import { TIMEZONES, WORK_STATUSES, SCHEDULE_TYPES } from '../../../logic/constants/index.js'
import { finalPrice, discountAmount } from '../../../logic/utils/index.js'
import { useRosterStore } from '../../../logic/store/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const showTour = ref(false)

const loading = ref(true)
const saving = ref(false)
const saveMsg = ref('')
const saveErr = ref('')
const loadErr = ref('')
const students = computed(() => useRosterStore().students)
const showStudentPicker = ref(false)
useEscapeKey(() => showStudentPicker.value, () => { showStudentPicker.value = false })

const defaultForm = () => ({
  timezone_offset: 3,
  work_status: 'WORKING',
  schedule_type: 'INFORMATIVE',
  display_time_from: '08:00',
  display_time_to: '22:00',
  self_booking_mode: 'YES',
  self_booking_whitelist: [],
  booking_lead_time_hours: 24,
  cancellation_lead_time_hours: 24,
  default_links: [],
  hourly_rate: 0,
  discount: 0,
})

const form = reactive(defaultForm())

function studentName(studentId) {
  const s = students.value.find(x => x.student_id === studentId)
  return s ? s.full_name : `#${studentId}`
}

const availableForWhitelist = computed(() => {
  const current = form.self_booking_whitelist || []
  return students.value.filter(s => !current.includes(s.student_id))
})

function addToWhitelist(studentId) {
  if (!form.self_booking_whitelist) form.self_booking_whitelist = []
  form.self_booking_whitelist.push(studentId)
  showStudentPicker.value = false
}

function removeFromWhitelist(studentId) {
  form.self_booking_whitelist = (form.self_booking_whitelist || []).filter(id => id !== studentId)
}

function toggleSelfBooking() {
  form.self_booking_mode = form.self_booking_mode === 'YES' ? 'NO' : 'YES'
}

function addLink() {
  form.default_links.push({ alias: '', url: '', _urlErr: '' })
}

function removeLink(i) {
  form.default_links.splice(i, 1)
}

function validateUrl(url) {
  if (!url) return true
  try {
    const u = new URL(url)
    return u.protocol === 'https:'
  } catch {
    return false
  }
}

function validateLinks() {
  let ok = true
  for (const link of form.default_links) {
    link._urlErr = ''
    if (link.url && !validateUrl(link.url)) {
      link._urlErr = 'Только https:// ссылки'
      ok = false
    }
  }
  return ok
}

function applyProfile(data) {
  Object.assign(form, {
    timezone_offset: data.timezone_offset,
    work_status: data.work_status,
    schedule_type: data.schedule_type,
    display_time_from: data.display_time_from,
    display_time_to: data.display_time_to,
    self_booking_mode: data.self_booking_mode,
    self_booking_whitelist: data.self_booking_whitelist || [],
    booking_lead_time_hours: data.booking_lead_time_hours,
    cancellation_lead_time_hours: data.cancellation_lead_time_hours,
    default_links: (data.default_links || []).map(l => ({ ...l, _urlErr: '' })),
    hourly_rate: data.hourly_rate,
    discount: data.discount,
  })
}

async function handleSave() {
  saveMsg.value = ''
  saveErr.value = ''
  if (!validateLinks()) return

  saving.value = true
  try {
    const data = await saveTutorSettings({
      timezone_offset: form.timezone_offset,
      work_status: form.work_status,
      schedule_type: form.schedule_type,
      display_time_from: form.display_time_from,
      display_time_to: form.display_time_to,
      self_booking_mode: form.self_booking_mode,
      self_booking_whitelist: form.self_booking_whitelist || [],
      booking_lead_time_hours: form.booking_lead_time_hours,
      cancellation_lead_time_hours: form.cancellation_lead_time_hours,
      default_links: form.default_links.map(l => ({ alias: l.alias, url: l.url })),
      hourly_rate: form.hourly_rate,
      discount: form.discount,
    })
    applyProfile(data)
    saveMsg.value = 'Настройки сохранены'
    logInfo('settings', 'save:ok')
    setTimeout(() => saveMsg.value = '', 3000)
  } catch (e) {
    if (e.status) {
      saveErr.value = e.message || 'Ошибка сохранения'
      logError('settings', 'save:fail', { status: e.status, error: e.payload?.error })
    } else {
      saveErr.value = 'Сеть'
      logError('settings', 'save:networkError', { error: e.message })
    }
  } finally { saving.value = false }
}

async function handleReset() {
  if (!confirm('Сбросить настройки к значениям по умолчанию? Ссылки, ставка и самозапись не изменятся.')) return
  saveMsg.value = ''
  saveErr.value = ''
  saving.value = true
  try {
    const data = await saveTutorSettings({
      discount: 0,
      timezone_offset: 0,
      work_status: 'WORKING',
      schedule_type: 'MINIMALISTIC',
      display_time_from: '00:00',
      display_time_to: '23:59',
    })
    applyProfile(data)
    saveMsg.value = 'Настройки сброшены'
    logInfo('settings', 'reset:ok')
    setTimeout(() => saveMsg.value = '', 3000)
  } catch (e) {
    if (e.status) {
      saveErr.value = e.message || 'Ошибка сброса'
      logError('settings', 'reset:fail', { status: e.status, error: e.payload?.error })
    } else {
      saveErr.value = 'Сеть'
      logError('settings', 'reset:networkError', { error: e.message })
    }
  } finally { saving.value = false }
}

onMounted(async () => {
  logInfo('settings', 'mounted:loading')
  loadErr.value = ''
  try {
    try {
      const data = await loadTutorProfile()
      applyProfile(data)
      logInfo('settings', 'mounted:profileLoaded')
    } catch (e) {
      if (!e.status) throw e
      loadErr.value = 'Не удалось загрузить настройки'
    }
    try {
      await loadTutorStudents()
      logInfo('settings', 'mounted:studentsLoaded', { count: students.value.length })
    } catch {
      // Как раньше: падение списка учеников молчаливое.
    }
  } catch (e) {
    loadErr.value = 'Сеть'
    logError('settings', 'mounted:error', { error: e.message })
  } finally { loading.value = false }
})
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; }
.load-err { margin-bottom: 12px; }

.card {
  background: var(--surface); border-radius: 12px; border: 1px solid var(--color-gray-200);
  padding: 20px; display: flex; flex-direction: column; gap: 14px; margin-bottom: 16px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--color-primary); margin: 0; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-col { display: flex; flex-direction: column; gap: 12px; }
.frow { display: flex; gap: 14px; }
.frow > .fl { flex: 1; }

/* Примитивы .fl/.ferr/.pick-empty/.fmsg — из base.css (single source). */

.input-with-suffix { display: flex; align-items: center; gap: 6px; }
.input-with-suffix input { flex: 1; }
.suffix { font-size: 13px; color: var(--color-gray-600); white-space: nowrap; }

.final-price {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  background: var(--color-accent-50); border: 1px solid var(--color-accent-100); border-radius: 8px;
  margin-top: 4px;
}
.final-price-label { font-size: 13px; color: var(--color-gray-700); }
.final-price-val { font-size: 15px; font-weight: 600; color: var(--color-accent-dark); }
.final-price-save { font-size: 12px; color: var(--color-success); font-weight: 500; }

/* Whitelist */
.whitelist-section { display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px solid var(--color-gray-300); border-radius: 8px; background: var(--color-surface-subtle); transition: opacity 150ms; }
.whitelist-section--disabled { opacity: 0.45; pointer-events: none; }
.whitelist-head { display: flex; align-items: center; justify-content: space-between; }
.whitelist-title { font-size: 13px; font-weight: 500; color: var(--color-gray-700); }
/* .part-chip/.part-empty/.ferr/.pick-empty/.fmsg — из base.css (single source). */

.toggle-row { display: flex; align-items: center; gap: 12px; }
.toggle-label { font-size: 13px; font-weight: 500; color: var(--color-gray-700); }
.toggle-hint { font-size: 12px; color: var(--color-gray-600); }
.toggle { position: relative; display: inline-block; width: 40px; height: 22px; cursor: pointer; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-track {
  position: absolute; inset: 0; background: var(--color-gray-400); border-radius: 11px; transition: background 200ms;
}
.toggle-track::after {
  content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px;
  background: var(--surface); border-radius: 50%; transition: transform 200ms; box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle input:checked + .toggle-track { background: var(--color-accent); }
.toggle input:checked + .toggle-track::after { transform: translateX(18px); }

/* Links */
.links-list { display: flex; flex-direction: column; gap: 8px; }
.link-row { display: flex; gap: 8px; align-items: flex-start; }
.link-alias { width: 140px; padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.link-url { flex: 1; padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.link-alias:focus, .link-url:focus { outline: none; border-color: var(--color-accent); }
.input-err { border-color: var(--color-danger); }

/* .info-k — из base.css (single source). */

/* Save */
.save-bar { display: flex; align-items: center; gap: 12px; justify-content: flex-end; padding: 8px 0; }



.card { padding: 24px; gap: 16px; }
.form-col, .input-with-suffix { min-width: 0; }
.toggle-track::after { background: var(--toggle-thumb); }
.toggle input:focus-visible + .toggle-track { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 700px) { .form-grid { grid-template-columns: minmax(0, 1fr); } .card { padding: 16px; } .link-row { flex-wrap: wrap; } .link-url { flex-basis: 100%; } .final-price, .toggle-row { flex-wrap: wrap; } }
</style>
