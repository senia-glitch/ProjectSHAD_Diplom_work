<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="students-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Ученики</h1>
          <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
          <button class="btn btn--pri" @click="openModal">Добавить ученика</button>
        </div>
        <p class="page-desc">Ученики и их настройки</p>
      </div>
      <StudentsTour v-if="showTour" @close="showTour = false" />
      <div class="content-grid">
        <div class="list-panel">
          <div
            v-for="c in configurations"
            :key="c.config_id"
            class="list-item"
            :class="{ active: selected?.config_id === c.config_id }"
            role="button" tabindex="0"
            @keydown.enter.prevent="selectConfig(c)" @keydown.space.prevent="selectConfig(c)"
            @click="selectConfig(c)"
          >
            <div class="item-avatar">
              <span>{{ (c.student_full_name || studentName(c.student_id) || '?').charAt(0).toUpperCase() }}</span>
            </div>
            <div class="item-info">
              <span class="item-name">{{ c.student_full_name || studentName(c.student_id) }}</span>
              <span v-if="c.status === 'PENDING'" class="item-sub item-sub--pending">
                {{ c.requested_by === 'student' ? 'Просит добавить его — ответьте' : 'Ждёт согласия ученика' }}
              </span>
              <span class="item-sub" v-else-if="c.hourly_rate">{{ c.hourly_rate }} ₽/час</span>
            </div>
          </div>
          <div v-if="!configurations.length && !listError" class="empty">Нет учеников</div>
          <div v-if="listError" class="empty empty--err">{{ listError }}</div>
        </div>

        <div v-if="selected && selected.status === 'PENDING'" class="detail-panel">
          <div class="detail-header">
            <h2>{{ selected.student_full_name || studentName(selected.student_id) }}</h2>
          </div>
          <template v-if="selected.requested_by === 'student'">
            <p class="pending-text">Ученик просит добавить его в ваши ученики. Пока вы не ответите, связь не действует.</p>
            <div class="pending-actions">
              <button type="button" class="btn btn--pri btn--sm" :disabled="answering" @click="answerLink(true)">Принять</button>
              <button type="button" class="btn btn--dan btn--sm" :disabled="answering" @click="answerLink(false)">Отклонить</button>
            </div>
          </template>
          <template v-else>
            <p class="pending-text">Заявка отправлена. Связь появится, когда ученик подтвердит её.</p>
            <div class="pending-actions">
              <button type="button" class="btn btn--gry btn--sm" :disabled="answering" @click="withdrawLink">Отозвать заявку</button>
            </div>
          </template>
          <p v-if="answerErr" class="ferr">{{ answerErr }}</p>
        </div>

        <div class="detail-panel" v-else-if="selected">
          <div class="detail-header">
            <h2>{{ selectedDetail?.student_name || studentName(selected.student_id) }}</h2>
            <div class="detail-buttons" v-if="selectedDetail && !editing && detailTab === 'terms'">
              <button class="btn btn--pri btn--sm" @click="startEdit">Редактировать</button>
              <button class="btn btn--gry btn--sm" @click="resetToDefaults">Сбросить</button>
              <button class="btn btn--dan btn--sm" @click="deleteConfig">Удалить</button>
            </div>
          </div>

          <!-- Карточка ученика: персональные условия и всё, что с ним связано -->
          <div class="detail-tabs" role="tablist" aria-label="Карточка ученика">
            <button v-for="t in DETAIL_TABS" :key="t.key" type="button" role="tab" class="detail-tab" :class="{ active: detailTab === t.key }" :aria-selected="detailTab === t.key" :disabled="editing && t.key !== 'terms'" @click="detailTab = t.key">{{ t.label }}</button>
          </div>
          <StudentActivity v-if="detailTab !== 'terms'" :student-id="selected.student_id" :tab="detailTab" />
          <template v-else>
          <div v-if="detailLoading" class="detail-loading">Загрузка данных...</div>
          <div v-if="detailError" class="detail-loading detail-loading--err">{{ detailError }}</div>
          <div v-if="deleteError" class="fmsg fmsg--err">{{ deleteError }}</div>
          <div v-if="resetError" class="fmsg fmsg--err">{{ resetError }}</div>

          <template v-else-if="selectedDetail && !editing">
            <div v-if="updateMsg" class="fmsg fmsg--ok">{{ updateMsg }}</div>
            <div class="detail-grid">
              <div class="detail-field">
                <span class="detail-label">ID конфигурации</span>
                <span class="detail-value detail-value--mono">{{ selectedDetail.config_id }}</span>
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
              <div class="detail-field">
                <span class="detail-label">Самозапись</span>
                <span class="detail-value">{{ selectedDetail.allow_self_booking ? 'Разрешена' : 'Запрещена' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Запись</span>
                <span class="detail-value">{{ selectedDetail.auto_confirm_bookings === false ? 'По моему подтверждению' : 'Без подтверждения' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Запись возможна за (часов)</span>
                <span class="detail-value">{{ selectedDetail.booking_lead_time_hours ?? '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Отмена возможна за (часов)</span>
                <span class="detail-value">{{ selectedDetail.cancellation_lead_time_hours ?? '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Уведомления</span>
                <span class="detail-value">{{ selectedDetail.notifications_enabled ? 'Включены' : 'Выключены' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Уведомления за (часов)</span>
                <span class="detail-value">{{ selectedDetail.notification_lead_time_hours ?? '—' }}</span>
              </div>
              <div class="detail-field">
                <span class="detail-label">Неоплаченные уроки</span>
                <span class="detail-value">{{ selectedDetail.allow_unpaid_lesson ? 'Разрешены' : 'Запрещены' }}</span>
              </div>
              <div class="detail-field detail-field--full">
                <span class="detail-label">Заметки об ученике</span>
                <span class="detail-value">{{ selectedDetail.student_notes || '—' }}</span>
              </div>
              <div class="detail-field detail-field--full">
                <span class="detail-label">Ссылки</span>
                <span class="detail-value" v-if="!selectedDetail.default_links?.length">—</span>
                <ul class="detail-links" v-else>
                  <li v-for="(l, i) in selectedDetail.default_links" :key="i">
                    <a :href="safeUrl(l.url)" target="_blank" rel="noopener">{{ l.alias || l.url }}</a>
                  </li>
                </ul>
              </div>
            </div>
            <div v-if="selectedDetail.hourly_rate > 0 && selectedDetail.discount > 0" class="final-price">
              <span class="final-price-label">Итого для ученика:</span>
              <span class="final-price-val">{{ finalPrice(selectedDetail.hourly_rate, selectedDetail.discount) }} руб/час</span>
              <span class="final-price-save">−{{ discountAmount(selectedDetail.hourly_rate, selectedDetail.discount) }} руб</span>
            </div>
          </template>

          <form v-else-if="selectedDetail && editing" class="side-form" @submit.prevent="handleSave" novalidate>
            <div class="frow">
              <label class="fl">Ставка (₽/час)
                <input v-model.number="editForm.hourly_rate" type="number" min="0" step="100" />
              </label>
              <label class="fl">Скидка (%)
                <input v-model.number="editForm.discount" type="number" min="0" max="100" step="5" />
              </label>
            </div>
            <div v-if="editForm.hourly_rate > 0 && editForm.discount > 0" class="final-price">
              <span class="final-price-label">Итого для ученика:</span>
              <span class="final-price-val">{{ finalPrice(editForm.hourly_rate, editForm.discount) }} руб/час</span>
              <span class="final-price-save">−{{ discountAmount(editForm.hourly_rate, editForm.discount) }} руб</span>
            </div>
            <label class="fl">Уведомления за (часов)
              <input v-model.number="editForm.notification_lead_time_hours" type="number" min="0" />
            </label>
            <label class="fl">Шаг записи (мин)
              <select v-model.number="editForm.slot_step_minutes">
                <option v-for="s in SLOT_STEP_OPTIONS" :key="s" :value="s">{{ s }} мин</option>
              </select>
            </label>
            <label class="fl checkbox-label">
              <input v-model="editForm.link_visibility_enabled" type="checkbox" /> Регулировать видимость ссылок
            </label>
            <label class="fl" v-if="editForm.link_visibility_enabled">Ссылки появляются за (мин)
              <input v-model.number="editForm.link_lead_time_minutes" type="number" min="0" max="15" step="1" />
            </label>
            <div class="frow">
              <label class="fl">Запись возможна за (часов)
                <input v-model.number="editForm.booking_lead_time_hours" type="number" min="0" max="168" />
              </label>
              <label class="fl">Отмена возможна за (часов)
                <input v-model.number="editForm.cancellation_lead_time_hours" type="number" min="0" max="168" />
              </label>
            </div>
            <div v-if="editErrors.numbers" class="ferr">{{ editErrors.numbers }}</div>
            <label class="fl checkbox-label">
              <input v-model="editForm.allow_self_booking" type="checkbox" /> Самозапись разрешена
            </label>
            <label class="fl checkbox-label">
              <input v-model="editForm.auto_confirm_bookings" type="checkbox" /> Запись без моего подтверждения
            </label>
            <label class="fl checkbox-label">
              <input v-model="editForm.notifications_enabled" type="checkbox" /> Уведомления включены
            </label>
            <label class="fl checkbox-label">
              <input v-model="editForm.allow_unpaid_lesson" type="checkbox" /> Неоплаченные уроки разрешены
            </label>
            <label class="fl">Заметки об ученике
              <textarea v-model="editForm.student_notes" rows="2" placeholder="Необязательно"></textarea>
            </label>
            <div class="links-section">
              <div class="links-head">
                <span class="links-title">Ссылки</span>
                <button
                  v-if="editForm.default_links.length < 10"
                  type="button"
                  class="icon-btn icon-btn--add"
                  @click="addLink"
                  title="Добавить ссылку"
                 aria-label="Добавить ссылку">+</button>
              </div>
              <div v-if="!editForm.default_links.length" class="pick-empty">Нет ссылок</div>
              <div v-for="(link, i) in editForm.default_links" :key="i" class="link-row">
                <input v-model="link.alias" placeholder="Название" class="link-alias" />
                <input
                  v-model="link.url"
                  placeholder="https://..."
                  class="link-url"
                  :class="{ 'input-err': link._urlErr || link._aliasErr }"
                />
                <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" @click="removeLink(i)">−</button>
                <div v-if="link._urlErr" class="ferr">{{ link._urlErr }}</div>
                <div v-if="link._aliasErr" class="ferr">{{ link._aliasErr }}</div>
              </div>
              <div v-if="editForm.default_links.length >= 10" class="pick-empty">Максимум 10 ссылок</div>
            </div>
            <div v-if="editMsg" class="fmsg fmsg--ok">{{ editMsg }}</div>
            <div v-if="editErr" class="fmsg fmsg--err">{{ editErr }}</div>
            <div class="info-actions">
              <button type="submit" class="btn btn--pri btn--sm" :disabled="saving">{{ saving ? '...' : 'Сохранить' }}</button>
              <button type="button" class="btn btn--gry btn--sm" @click="cancelEdit">Отмена</button>
            </div>
          </form>
          </template>
        </div>

        <div class="detail-panel detail-panel--empty" v-else>
          <p>Выберите ученика</p>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="add-student-title">
          <h3 id="add-student-title" class="modal-title">Добавить ученика</h3>
          <p class="modal-desc">Введите личный код ученика — он указан в его профиле</p>
          <div class="form-group">
            <label class="form-label" for="personal-code">Личный код</label>
            <input
              id="personal-code"
              v-model="personalCode"
              class="form-input"
              :class="{ 'form-input--error': addError }"
              type="text"
              placeholder="Например: IND-AB12CD34"
              autocomplete="off"
              @keyup.enter="addStudent"
              :disabled="addLoading"
            />
            <span class="form-error" v-if="addError">{{ addError }}</span>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn--gry" @click="closeModal" :disabled="addLoading">Отмена</button>
            <button type="button" class="btn btn--pri" @click="addStudent" :disabled="addLoading || !personalCode.trim()">
              {{ addLoading ? 'Добавление…' : 'Добавить' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import StudentsTour from './StudentsTour.vue'
import StudentActivity from './StudentActivity.vue'
import { useUser, useLogout, useEscapeKey } from '../../composables/index.js'
import {
  loadTutorStudents,
  loadTutorConfigurations,
  loadTutorConfiguration,
  addStudentByCode,
  answerLinkAsTutor,
  updateTutorConfiguration,
  resetTutorConfiguration,
  removeTutorConfiguration,
} from '../../../logic/actions/index.js'
import { finalPrice, discountAmount, safeUrl } from '../../../logic/utils/index.js'
import { SLOT_STEP_OPTIONS, SLOT_STEP_DEFAULT } from '../../../logic/constants/index.js'
import { logError, logInfo } from '../../../logic/logger/index.js'
import { useRosterStore } from '../../../logic/store/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const showTour = ref(false)
const rosterStore = useRosterStore()
const configurations = computed(() => rosterStore.configurations)
const students = computed(() => rosterStore.students)

const selected = ref(null)
const selectedDetail = ref(null)
const loading = ref(true)
const detailLoading = ref(false)
const listError = ref('')
const detailError = ref('')
const deleteError = ref('')
const resetError = ref('')
const updateMsg = ref('')

const editing = ref(false)
const saving = ref(false)
const editMsg = ref('')
const editErr = ref('')
const editErrors = reactive({ numbers: '' })
const editForm = reactive({
  hourly_rate: 0,
  discount: 0,
  slot_step_minutes: SLOT_STEP_DEFAULT,
  link_visibility_enabled: false,
  link_lead_time_minutes: 0,
  allow_self_booking: true,
  auto_confirm_bookings: true,
  booking_lead_time_hours: 24,
  cancellation_lead_time_hours: 24,
  notifications_enabled: true,
  notification_lead_time_hours: 24,
  allow_unpaid_lesson: false,
  student_notes: '',
  default_links: [],
})

// Заявки о связи: ответ (входящая) или отзыв (своя).
const answering = ref(false)
const answerErr = ref('')

async function answerLink(accept) {
  if (!selected.value) return
  answering.value = true
  answerErr.value = ''
  try {
    await answerLinkAsTutor(selected.value.config_id, accept)
    const fresh = configurations.value.find((c) => c.config_id === selected.value.config_id)
    selected.value = null
    if (fresh) await selectConfig(fresh)
  } catch (e) {
    answerErr.value = e.message || 'Не удалось ответить на заявку'
  } finally {
    answering.value = false
  }
}

async function withdrawLink() {
  if (!selected.value || !window.confirm('Отозвать заявку на связь с учеником?')) return
  answering.value = true
  answerErr.value = ''
  try {
    await removeTutorConfiguration(selected.value.config_id)
    selected.value = null
  } catch (e) {
    answerErr.value = e.message || 'Не удалось отозвать заявку'
  } finally {
    answering.value = false
  }
}

const showModal = ref(false)
const personalCode = ref('')
const addError = ref('')
const addLoading = ref(false)
useEscapeKey(() => showModal.value && !addLoading.value, () => closeModal())

function studentName(studentId) {
  const s = students.value.find((x) => x.student_id === studentId)
  return s ? s.full_name : `Ученик #${studentId}`
}

function studentInitial(studentId) {
  const name = studentName(studentId)
  return (name || '?').charAt(0).toUpperCase()
}

async function fetchRoster() {
  loading.value = true
  listError.value = ''
  try {
    await Promise.all([loadTutorStudents(), loadTutorConfigurations()])
  } catch (e) {
    listError.value = e.status ? 'Не удалось загрузить список учеников' : 'Сеть'
    logError('students', 'fetchRoster:error', { error: e.message })
  }
  loading.value = false
}

// Порядковый номер запроса деталей: последний клик заменяет
// «последний запрос», устаревший ответ не перезаписывает панель
// данными другого ученика.
let detailSeq = 0

const DETAIL_TABS = [
  { key: 'terms', label: 'Условия' },
  { key: 'lessons', label: 'Уроки' },
  { key: 'payments', label: 'Оплаты' },
  { key: 'tests', label: 'Тесты' },
]
const detailTab = ref('terms')

async function selectConfig(c) {
  selected.value = c
  detailTab.value = 'terms'
  selectedDetail.value = null
  editing.value = false
  updateMsg.value = ''
  deleteError.value = ''
  resetError.value = ''
  detailLoading.value = true
  detailError.value = ''
  const my = ++detailSeq
  try {
    const detail = await loadTutorConfiguration(c.config_id)
    if (my !== detailSeq) return
    selectedDetail.value = {
      ...detail,
      student_name: studentName(detail.student_id),
    }
  } catch (e) {
    if (my === detailSeq) {
      detailError.value = e.status ? 'Не удалось загрузить данные ученика' : 'Сеть'
    }
    logError('students', 'selectConfig:error', { error: e.message })
  } finally {
    if (my === detailSeq) detailLoading.value = false
  }
}

function startEdit() {
  if (!selectedDetail.value) return
  const d = selectedDetail.value
  editing.value = true
  editMsg.value = ''
  editErr.value = ''
  editErrors.numbers = ''
  updateMsg.value = ''
  editForm.hourly_rate = d.hourly_rate ?? 0
  editForm.discount = d.discount ?? 0
  editForm.slot_step_minutes = d.slot_step_minutes ?? SLOT_STEP_DEFAULT
  editForm.link_visibility_enabled = d.link_visibility_enabled ?? false
  editForm.link_lead_time_minutes = d.link_lead_time_minutes ?? 0
  editForm.allow_self_booking = d.allow_self_booking ?? true
  editForm.auto_confirm_bookings = d.auto_confirm_bookings ?? true
  editForm.booking_lead_time_hours = d.booking_lead_time_hours ?? 24
  editForm.cancellation_lead_time_hours = d.cancellation_lead_time_hours ?? 24
  editForm.notifications_enabled = d.notifications_enabled ?? true
  editForm.notification_lead_time_hours = d.notification_lead_time_hours ?? 24
  editForm.allow_unpaid_lesson = d.allow_unpaid_lesson ?? false
  editForm.student_notes = d.student_notes || ''
  editForm.default_links = (d.default_links || []).map((l) => ({ ...l, _urlErr: '', _aliasErr: '' }))
}

function cancelEdit() {
  editing.value = false
  editMsg.value = ''
  editErr.value = ''
  editErrors.numbers = ''
}

function addLink() {
  if (editForm.default_links.length >= 10) return
  editForm.default_links.push({ alias: '', url: '', _urlErr: '', _aliasErr: '' })
}

function removeLink(i) {
  editForm.default_links.splice(i, 1)
}

function isHttpsUrl(url) {
  try {
    return new URL(url).protocol === 'https:'
  } catch {
    return false
  }
}

function validateEdit() {
  editErrors.numbers = ''
  editMsg.value = ''
  editErr.value = ''
  const nums = [
    ['hourly_rate', editForm.hourly_rate, 0, null],
    ['discount', editForm.discount, 0, 100],
    ['slot_step_minutes', editForm.slot_step_minutes, 1, null],
    ['link_lead_time_minutes', editForm.link_lead_time_minutes, 0, 15],
    ['booking_lead_time_hours', editForm.booking_lead_time_hours, 0, 168],
    ['cancellation_lead_time_hours', editForm.cancellation_lead_time_hours, 0, 168],
    ['notification_lead_time_hours', editForm.notification_lead_time_hours, 0, null],
  ]
  for (const [, v, min, max] of nums) {
    if (typeof v !== 'number' || Number.isNaN(v) || v < min || (max !== null && v > max)) {
      editErrors.numbers = 'Числа: ставка ≥ 0, скидка 0–100, шаг ≥ 1, ссылки за 0–15, лид-таймы 0–168, уведомления за ≥ 0'
      return false
    }
  }
  let ok = true
  for (const link of editForm.default_links) {
    link._urlErr = ''
    link._aliasErr = ''
    const alias = (link.alias || '').trim()
    const url = (link.url || '').trim()
    if (!alias && !url) continue
    if (url && !alias) {
      link._aliasErr = 'Введите название ссылки'
      ok = false
    }
    if (alias && !url) {
      link._urlErr = 'Введите адрес ссылки'
      ok = false
    }
    if (url && !isHttpsUrl(url)) {
      link._urlErr = 'Только https:// ссылки'
      ok = false
    }
  }
  return ok
}

async function handleSave() {
  if (!selected.value || !validateEdit()) return
  saving.value = true
  editErr.value = ''
  try {
    const patch = {
      hourly_rate: editForm.hourly_rate,
      discount: editForm.discount,
      slot_step_minutes: editForm.slot_step_minutes,
      link_visibility_enabled: editForm.link_visibility_enabled,
      link_lead_time_minutes: editForm.link_lead_time_minutes,
      allow_self_booking: editForm.allow_self_booking,
      auto_confirm_bookings: editForm.auto_confirm_bookings,
      booking_lead_time_hours: editForm.booking_lead_time_hours,
      cancellation_lead_time_hours: editForm.cancellation_lead_time_hours,
      notifications_enabled: editForm.notifications_enabled,
      notification_lead_time_hours: editForm.notification_lead_time_hours,
      default_links: editForm.default_links
        .filter((l) => (l.alias || '').trim() || (l.url || '').trim())
        .map((l) => ({ alias: (l.alias || '').trim(), url: (l.url || '').trim() })),
      allow_unpaid_lesson: editForm.allow_unpaid_lesson,
      student_notes: (editForm.student_notes || '').trim(),
    }
    const updated = await updateTutorConfiguration(selected.value.config_id, patch)
    selectedDetail.value = { ...updated, student_name: studentName(updated.student_id) }
    editing.value = false
    updateMsg.value = 'Сохранено'
    logInfo('students', 'update:ok', { id: selected.value.config_id })
    setTimeout(() => (updateMsg.value = ''), 3000)
  } catch (e) {
    editErr.value = e.status
      ? e.message || 'Ошибка сохранения'
      : 'Сеть'
    logError('students', 'update:fail', { error: e.message })
  } finally {
    saving.value = false
  }
}

async function resetToDefaults() {
  if (!selected.value) return
  if (!confirm('Сбросить настройки ученика к значениям по умолчанию?')) return
  resetError.value = ''
  try {
    const updated = await resetTutorConfiguration(selected.value.config_id)
    selectedDetail.value = { ...updated, student_name: studentName(updated.student_id) }
    editing.value = false
    updateMsg.value = 'Сброшено к настройкам по умолчанию'
    logInfo('students', 'reset:ok', { id: selected.value.config_id })
    setTimeout(() => (updateMsg.value = ''), 3000)
  } catch (e) {
    resetError.value = e.status
      ? e.message || 'Ошибка сброса'
      : 'Сеть'
    logError('students', 'reset:fail', { error: e.message })
  }
}

async function deleteConfig() {  if (!selected.value) return
  if (!confirm('Удалить этого ученика?')) return
  deleteError.value = ''
  try {
    await removeTutorConfiguration(selected.value.config_id)
    selected.value = null
    selectedDetail.value = null
    editing.value = false
  } catch (e) {
    deleteError.value = e.status
      ? e.message || 'Ошибка удаления'
      : 'Сеть'
    logError('students', 'deleteConfig:error', { error: e.message })
  }
}

function openModal() {
  personalCode.value = ''
  addError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  addError.value = ''
}

async function addStudent() {
  const code = personalCode.value.trim()
  if (!code) {
    addError.value = 'Введите личный код ученика'
    return
  }
  addError.value = ''
  addLoading.value = true
  try {
    const data = await addStudentByCode({ personalNumber: code })
    const created = configurations.value.find((c) => c.config_id === data.config_id)
    closeModal()
    if (created) await selectConfig(created)
  } catch (e) {
    addError.value = e.status
      ? e.message || 'Ошибка добавления'
      : 'Ошибка сети'
  } finally {
    addLoading.value = false
  }
}

onMounted(fetchRoster)
</script>

<style scoped>
.item-sub--pending { color: var(--rule-only-border, #d4a72c); }
.pending-text { margin: 12px 0; color: var(--muted, var(--color-gray-600)); font-size: 14px; line-height: 1.5; }
.pending-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.students-page { display: flex; flex-direction: column; }
.content-grid { display: grid; grid-template-columns: 300px 1fr; gap: 16px; min-height: 400px; }

.list-panel { background: var(--color-white); border-radius: var(--radius-lg); border: 1px solid var(--color-gray-200); overflow: hidden; }
.list-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  cursor: pointer; border-bottom: 1px solid var(--color-gray-100); transition: background 150ms;
}
.list-item:hover { background: var(--color-gray-50); }
.list-item.active { background: var(--color-accent-50); border-left: 3px solid var(--color-accent); }
.item-avatar {
  width: 40px; height: 40px; border-radius: var(--radius-full); background: var(--accent);
  display: flex; align-items: center; justify-content: center; color: var(--on-accent); font-weight: 600;
}
.item-info { display: flex; flex-direction: column; gap: 2px; }
.item-name { font-weight: 500; color: var(--color-gray-800); }
.item-sub { font-size: 12px; color: var(--color-gray-600); }

.detail-panel { background: var(--color-white); border-radius: var(--radius-lg); border: 1px solid var(--color-gray-200); padding: 24px; }
.detail-tabs { display: flex; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid var(--line); margin: 4px 0 16px; }
.detail-tab { border: 0; background: none; color: var(--muted); font: inherit; font-size: 14px; padding: 8px 12px; border-bottom: 2px solid transparent; margin-bottom: -1px; cursor: pointer; }
.detail-tab:hover:not(:disabled) { color: var(--text); }
.detail-tab.active { color: var(--text); border-bottom-color: var(--accent); font-weight: 500; }
.detail-tab:disabled { opacity: .5; cursor: not-allowed; }
.detail-panel--empty { display: flex; align-items: center; justify-content: center; color: var(--color-gray-500); }
/* .detail-header/.detail-label/.detail-value — из base.css (single source). */
.detail-buttons { display: flex; gap: 6px; }
.detail-loading { padding: 24px; text-align: center; color: var(--color-gray-500); }
.detail-loading--err { color: var(--color-danger); }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.detail-field { display: flex; flex-direction: column; gap: 4px; }
.detail-field--full { grid-column: 1 / -1; }
/* .detail-label/.detail-value — из base.css (single source). */
.detail-value--mono { font-family: monospace; font-size: 13px; }
.detail-links { display: flex; flex-direction: column; gap: 4px; font-size: 14px; }

.final-price {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  background: var(--color-accent-50); border: 1px solid var(--color-accent-100); border-radius: 8px;
  margin-top: 16px;
}
.final-price-label { font-size: 13px; color: var(--color-gray-700); }
.final-price-val { font-size: 15px; font-weight: 600; color: var(--color-accent-dark); }
.final-price-save { font-size: 12px; color: var(--color-success); font-weight: 500; }

.side-form { display: flex; flex-direction: column; gap: 10px; }
/* .info-actions — из base.css (single source). */
.checkbox-label { flex-direction: row; align-items: center; gap: 8px; }
.checkbox-label input { width: auto; }
.fl textarea {
  padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: var(--radius-md);
  font-size: 13px; background: var(--color-white); width: 100%; box-sizing: border-box;
  font-family: inherit; resize: vertical;
}
.fl textarea:focus { outline: none; border-color: var(--color-accent); }

.links-section { display: flex; flex-direction: column; gap: 8px; }
.links-head { display: flex; align-items: center; justify-content: space-between; }
.links-title { font-size: 13px; font-weight: 500; color: var(--color-gray-700); }
.link-row { display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap; }
.link-alias { width: 140px; padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: var(--radius-md); font-size: 13px; box-sizing: border-box; }
.link-url { flex: 1; min-width: 160px; padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: var(--radius-md); font-size: 13px; box-sizing: border-box; }
.link-alias:focus, .link-url:focus { outline: none; border-color: var(--color-accent); }
.input-err { border-color: var(--color-danger); }
.link-row .ferr { flex-basis: 100%; }

/* .ferr — из base.css (single source). */
.modal-desc { margin: 0 0 20px; font-size: 14px; color: var(--color-gray-600); }
.form-input--error { border-color: var(--color-danger); }
.form-error { font-size: 12px; color: var(--color-danger); min-height: 16px; }
.empty--err { color: var(--color-danger); }

.content-grid { grid-template-columns: minmax(240px, 300px) minmax(0, 1fr); }
.list-panel, .detail-panel { min-width: 0; }
.item-info { min-width: 0; overflow-wrap: anywhere; }
@media (max-width: 850px) { .content-grid { grid-template-columns: minmax(0, 1fr); } .list-panel { max-height: 280px; overflow-y: auto; } .detail-panel--empty { min-height: 180px; } }
@media (max-width: 600px) { .detail-grid { grid-template-columns: minmax(0, 1fr); } .detail-panel { padding: 16px; } .link-row { flex-wrap: wrap; } .link-url { min-width: 0; flex-basis: 100%; } }
</style>
