<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="tutors-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Репетиторы</h1>
          <span class="header-actions">
            <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
            <button class="btn btn--pri" @click="showAddModal = true">Добавить репетитора</button>
          </span>
        </div>
        <p class="page-desc">Репетиторы и их настройки</p>
        <p v-if="myCode" class="my-code">Ваш личный код: <span class="mono">{{ myCode }}</span> — сообщите его репетитору для связи</p>
      </div>
      <TutorsTour v-if="showTour" @close="showTour = false" />
      <div class="content-grid">
        <div class="list-panel">
          <div
            v-for="c in configurations"
            :key="c.config_id"
            class="list-item"
            :class="{ active: selected?.config_id === c.config_id }"
            @click="selectConfig(c)"
          >
            <div class="item-avatar">
              <span>{{ (c.tutor_username || '?').charAt(0).toUpperCase() }}</span>
            </div>
            <div class="item-info">
              <span class="item-name">{{ c.tutor_full_name || c.tutor_username }}</span>
              <span class="item-sub" v-if="c.hourly_rate">{{ c.hourly_rate }} ₽/час</span>
            </div>
          </div>
          <div v-if="!configurations.length && !loading && !listError" class="empty">
            Нет репетиторов
          </div>
          <div v-if="listError" class="empty" style="color:var(--color-danger)">{{ listError }}</div>
          <div v-if="loading" class="loading">Загрузка...</div>
        </div>

        <div class="detail-panel" v-if="selected">
          <div class="detail-header">
            <h2>{{ selectedDetail?.tutor_full_name || selected.tutor_username || 'Загрузка...' }}</h2>
            <button class="btn btn--dan btn--sm" @click="deleteConfig">Удалить</button>
          </div>

          <div v-if="detailLoading" class="detail-loading">Загрузка данных...</div>
          <div v-if="detailError" class="detail-loading detail-loading--err">{{ detailError }}</div>
          <div v-if="deleteError" class="detail-loading detail-loading--err">{{ deleteError }}</div>

          <template v-else-if="selectedDetail">
            <div class="detail-grid">
              <div class="detail-field">
                <span class="detail-label">Имя пользователя</span>
                <span class="detail-value">{{ selectedDetail.tutor_username }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Полное имя</span>
                <span class="detail-value">{{ selectedDetail.tutor_full_name || '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Статус работы</span>
                <span class="detail-value">{{ selectedDetail.tutor_work_status || '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Ставка (₽/час)</span>
                <span class="detail-value">{{ selectedDetail.hourly_rate ?? '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Скидка (%)</span>
                <span class="detail-value">{{ selectedDetail.discount ?? '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">ID конфигурации</span>
                <span class="detail-value detail-value--mono">{{ selectedDetail.config_id }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Самозапись</span>
                <span class="detail-value">{{ selectedDetail.allow_self_booking ? 'Разрешена' : 'Запрещена' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Шаг записи (мин)</span>
                <span class="detail-value">{{ selectedDetail.slot_step_minutes ?? '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Видимость ссылок</span>
                <span class="detail-value">{{ selectedDetail.link_visibility_enabled ? 'Регулируется' : 'Всегда видны' }}</span>
              </div>
              <div class="detail-field" v-if="selectedDetail.link_visibility_enabled">
                <span class="detail-label">Ссылки за (мин)</span>
                <span class="detail-value">{{ selectedDetail.link_lead_time_minutes ?? '—' }}</span>
              </div>
            </div>
            <div v-if="selectedDetail.hourly_rate > 0 && selectedDetail.discount > 0" class="final-price">
              <span class="final-price-label">Итого для вас:</span>
              <span class="final-price-val">{{ finalPrice(selectedDetail.hourly_rate, selectedDetail.discount) }} руб/час</span>
              <span class="final-price-save">−{{ discountAmount(selectedDetail.hourly_rate, selectedDetail.discount) }} руб</span>
            </div>
          </template>
        </div>

        <div class="detail-panel detail-panel--empty" v-else>
          <p>Выберите репетитора</p>
        </div>
      </div>
    </div>

    <div class="modal-overlay" v-if="showAddModal" @click.self="closeModal">
      <div class="modal">
        <h3 class="modal-title">Добавить репетитора</h3>
        <p class="modal-desc">Введите табельный номер репетитора</p>
        <div class="form-group">
          <label class="form-label" for="personal_number">Табельный номер</label>
          <input
            id="personal_number"
            v-model="personalNumber"
            class="form-input"
            :class="{ 'form-input--error': formError }"
            type="text"
            placeholder="Например: 12345"
            @keyup.enter="addTutor"
            :disabled="addLoading"
          />
          <span class="form-error" v-if="formError">{{ formError }}</span>
        </div>
          <div class="modal-actions">
            <button class="btn btn--gry" @click="closeModal" :disabled="addLoading">Отмена</button>
            <button class="btn btn--pri" @click="addTutor" :disabled="addLoading || !personalNumber.trim()">
            {{ addLoading ? 'Добавление...' : 'Добавить' }}
          </button>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import TutorsTour from './TutorsTour.vue'
import { useUser, useLogout } from '../../composables/index.js'
import {
  loadStudentConfigurations,
  loadStudentConfiguration,
  addTutorByCode,
  removeStudentConfiguration,
  loadMyProfile,
} from '../../../logic/actions/index.js'
import { logError } from '../../../logic/logger/index.js'
import { finalPrice, discountAmount } from '../../../logic/utils/index.js'
import { useRosterStore } from '../../../logic/store/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const rosterStore = useRosterStore()
const configurations = computed(() => rosterStore.configurations)
const selected = ref(null)
const selectedDetail = ref(null)
const loading = ref(true)
const detailLoading = ref(false)
const listError = ref('')
const detailError = ref('')
const deleteError = ref('')

const showAddModal = ref(false)
const showTour = ref(false)
const personalNumber = ref('')
const formError = ref('')
const addLoading = ref(false)
const myCode = ref('')

async function fetchConfigurations() {
  loading.value = true
  listError.value = ''
  try {
    await loadStudentConfigurations()
  } catch (e) {
    listError.value = e.status ? 'Не удалось загрузить список репетиторов' : 'Сеть'
    logError('tutors', 'fetchConfigurations:error', { error: e.message })
  }
  loading.value = false
}

// Порядковый номер запроса деталей: последний клик заменяет
// «последний запрос», устаревший ответ не перезаписывает панель
// данными другого репетитора.
let detailSeq = 0

async function selectConfig(config) {
  selected.value = config
  selectedDetail.value = null
  detailLoading.value = true
  detailError.value = ''
  const my = ++detailSeq
  try {
    const detail = await loadStudentConfiguration(config.config_id)
    if (my !== detailSeq) return
    selectedDetail.value = detail
  } catch (e) {
    if (my === detailSeq) {
      detailError.value = e.status ? 'Не удалось загрузить данные репетитора' : 'Сеть'
    }
    logError('tutors', 'selectConfig:error', { error: e.message })
  } finally {
    if (my === detailSeq) detailLoading.value = false
  }
}

async function deleteConfig() {
  if (!selected.value) return
  if (!confirm('Удалить этого репетитора?')) return
  deleteError.value = ''
  try {
    await removeStudentConfiguration(selected.value.config_id)
    selected.value = null
    selectedDetail.value = null
  } catch (e) {
    deleteError.value = e.status
      ? e.message || 'Ошибка удаления'
      : 'Сеть'
    logError('tutors', 'deleteConfig:error', { error: e.message })
  }
}

function closeModal() {
  showAddModal.value = false
  personalNumber.value = ''
  formError.value = ''
}

async function addTutor() {
  const code = personalNumber.value.trim()
  if (!code) {
    formError.value = 'Введите табельный номер'
    return
  }
  formError.value = ''
  addLoading.value = true
  try {
    const data = await addTutorByCode({ personalNumber: code })
    await fetchConfigurations()
    const newConfig = configurations.value.find((c) => c.config_id === data.config_id)
    if (newConfig) selectConfig(newConfig)
    closeModal()
  } catch (e) {
    formError.value = e.status
      ? e.message || 'Ошибка добавления'
      : 'Ошибка сети'
  }
  addLoading.value = false
}

onMounted(async () => {
  fetchConfigurations()
  try {
    const me = await loadMyProfile()
    myCode.value = me?.personal_number || ''
  } catch (e) {
    logError('tutors', 'fetchProfile:error', { error: e.message })
  }
})
</script>

<style scoped>
.tutors-page { display: flex; flex-direction: column; }
.header-actions { display: flex; align-items: center; gap: 8px; }
.my-code { font-size: 13px; color: var(--color-gray-700); margin: 8px 0 0; }
.my-code .mono { font-family: monospace; font-size: 13px; }

.content-grid { display: grid; grid-template-columns: 300px 1fr; gap: 16px; min-height: 400px; }

.list-panel { background: white; border-radius: 12px; border: 1px solid var(--color-gray-200); overflow: hidden; }
.list-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  cursor: pointer; border-bottom: 1px solid var(--color-gray-100); transition: background 150ms;
}
.list-item:hover { background: var(--color-gray-50); }
.list-item.active { background: rgba(58,122,189,0.1); border-left: 3px solid var(--color-accent); }
.item-avatar {
  width: 40px; height: 40px; border-radius: 50%; background: var(--color-primary);
  display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;
}
.item-info { display: flex; flex-direction: column; gap: 2px; }
.item-name { font-weight: 500; color: var(--color-gray-800); }
.item-sub { font-size: 12px; color: var(--color-gray-600); }

.detail-panel { background: white; border-radius: 12px; border: 1px solid var(--color-gray-200); padding: 24px; }
.detail-panel--empty { display: flex; align-items: center; justify-content: center; color: var(--color-gray-500); }
/* .detail-header/.detail-label/.detail-value — из base.css (single source). */
.detail-loading { padding: 24px; text-align: center; color: var(--color-gray-500); }
.detail-loading--err { color: var(--color-danger); }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.detail-field { display: flex; flex-direction: column; gap: 4px; }
/* .detail-label/.detail-value — из base.css (single source). */
.detail-value--mono { font-family: monospace; font-size: 13px; }

.final-price {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  background: var(--color-accent-50); border: 1px solid var(--color-accent-100); border-radius: 8px;
  margin-top: 16px;
}
.final-price-label { font-size: 13px; color: var(--color-gray-700); }
.final-price-val { font-size: 15px; font-weight: 600; color: var(--color-accent-dark); }
.final-price-save { font-size: 12px; color: var(--color-success); font-weight: 500; }

.modal-desc { margin: 0 0 20px; font-size: 14px; color: var(--color-gray-600); }
.form-input--error { border-color: var(--color-danger); }
.form-error { font-size: 12px; color: var(--color-danger); min-height: 16px; }
</style>
