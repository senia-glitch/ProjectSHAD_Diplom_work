<template>
  <div class="side-block side-block--info">
    <h3 class="side-title">Информация</h3>
    <template v-if="!selectedLessons.length">
      <p class="side-hint">Выберите урок для получения информации</p>
    </template>
    <template v-else>
      <div class="info-scroll">
        <div v-for="l in selectedLessons" :key="l.lesson_id" class="info-card">
          <!-- View mode -->
          <template v-if="editingId !== l.lesson_id">
            <div class="info-rows">
              <div class="info-r"><span class="info-k">Урок</span><span class="info-v">#{{ l.lesson_id }}</span></div>
              <div class="info-r"><span class="info-k">Начало</span><span class="info-v">{{ fmtDateTime(l.start_time) }}</span></div>
              <div class="info-r"><span class="info-k">Конец</span><span class="info-v">{{ fmtDateTime(l.end_time) }}</span></div>
              <div class="info-r"><span class="info-k">Тип</span><span class="info-v">{{ l.is_group ? 'Групповой' : 'Индивидуальный' }}</span></div>
              <div class="info-r"><span class="info-k">Статус</span><span class="info-v">{{ statusLabel(l.status) }}</span></div>
              <div class="info-r"><span class="info-k">Ссылки</span>
                <span v-if="!l.lesson_links?.length" class="info-v">—</span>
                <span v-else-if="role !== 'student' || linksVisible(l)" class="link-list">
                  <a v-for="(link, i) in l.lesson_links" :key="i" :href="safeUrl(link.url)" target="_blank" rel="noopener">{{ link.alias || link.url }}</a>
                </span>
                <span v-else class="pick-empty">Появятся за {{ linksRemaining(l) }} мин</span>
              </div>
            </div>
            <LessonNotes class="info-notes" :note="l.status_note" :absence="l.absence" />
            <div class="info-actions info-actions--lesson">
              <router-link :to="`/lessons/${l.lesson_id}`" class="btn btn--gry btn--sm">Открыть урок</router-link>
              <template v-if="role === 'tutor' && l.status === 'PENDING'">
                <button type="button" class="btn btn--pri btn--sm" :disabled="saving" @click="emit('confirm-request', l)">Подтвердить</button>
                <button type="button" class="btn btn--dan btn--sm" :disabled="saving" @click="emit('reject-request', l)">Отклонить</button>
              </template>
              <button
                v-if="role === 'student' && (l.status === 'SCHEDULED' || l.status === 'PENDING')"
                type="button"
                class="btn btn--dan btn--sm"
                :disabled="saving"
                @click="emit('cancel-lesson', l)"
              >{{ l.status === 'PENDING' ? 'Отозвать заявку' : 'Отменить' }}</button>
            </div>
                    <template v-if="role === 'tutor'">
                    <div class="part-section">
                      <div class="part-head">
                        <span class="info-k">Участники</span>
                        <button type="button" class="btn btn--gry btn--xs" @click="emit('load-participants', l.lesson_id)">
                  {{ participantsLoading[l.lesson_id] ? '...' : (participantsMap[l.lesson_id] ? 'Обновить' : 'Загрузить') }}
                </button>
              </div>
              <template v-if="participantsMap[l.lesson_id]">
                <div v-if="!participantsMap[l.lesson_id].length" class="part-empty">Нет участников</div>
                <div v-for="p in participantsMap[l.lesson_id]" :key="p.participant_id" class="part-chip">
                  <span>{{ studentName(p.student_user_id) }}</span>
                </div>
              </template>
            </div>
            <div class="info-actions">
              <button class="btn btn--pri btn--sm" @click="emit('start-edit', l)">Изменить</button>
              <button class="btn btn--dan btn--sm" @click="emit('delete-lesson', l)" :disabled="saving">{{ saving ? '...' : 'Удалить' }}</button>
            </div>
            </template>
          </template>
          <!-- Edit mode -->
          <template v-else>
            <form class="side-form" @submit.prevent="emit('save-lesson', l)" novalidate>
              <label class="fl">Начало
                <input v-model="editForm.start_time" type="datetime-local" />
              </label>
              <label class="fl">Окончание
                <input v-model="editForm.end_time" type="datetime-local" />
              </label>
              <label class="fl checkbox-label">
                <input type="checkbox" v-model="editForm.is_group" /> Групповой
              </label>
              <label class="fl">Статус
                <select v-model="editForm.status">
                  <option
                    v-if="!MANUAL_LESSON_STATUSES.some((s) => s.value === editForm.status)"
                    :value="editForm.status"
                    disabled
                  >{{ statusLabel(editForm.status) }} (текущий)</option>
                  <option v-for="s in MANUAL_LESSON_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
              </label>
              <!-- Edit participants -->
              <div class="edit-participants">
                <div class="part-head">
                  <span class="info-k">Участники</span>
                  <button v-if="editForm.is_group" type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить ученика" @click="emit('row-add')" :disabled="saving" aria-label="Добавить ученика">+</button>
                </div>
                <template v-if="!editForm.is_group">
                  <select v-model="singleEditStudent" class="add-part-select" :disabled="saving">
                    <option :value="null">— Без ученика —</option>
                    <option v-for="s in students" :key="s.user_id" :value="s.user_id">{{ s.full_name }}</option>
                  </select>
                </template>
                <template v-else>
                  <div v-if="!editRows.length" class="part-empty">Нет участников</div>
                  <div v-for="row in editRows" :key="row.key" class="add-part">
                    <select v-model="row.student_user_id" class="add-part-select" :disabled="saving">
                      <option :value="null" disabled>Выберите ученика</option>
                      <option
                        v-if="row.student_user_id && !students.some(s => s.user_id === row.student_user_id)"
                        :value="row.student_user_id" disabled
                      >{{ studentName(row.student_user_id) }}</option>
                      <option v-for="s in rowOptions(row.key)" :key="s.user_id" :value="s.user_id">{{ s.full_name }}</option>
                    </select>
                    <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать строку" @click="emit('row-remove', row.key)" :disabled="saving" aria-label="Убрать строку">−</button>
                  </div>
                </template>
                <div v-if="addParticipantErr" class="ferr">{{ addParticipantErr }}</div>
              </div>
              <div class="edit-links">
                <div class="part-head">
                  <span class="info-k">Ссылки урока</span>
                  <button type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить ссылку" @click="emit('link-add')" :disabled="saving" aria-label="Добавить ссылку">+</button>
                </div>
                <div v-if="!editForm.lesson_links?.length" class="part-empty">Нет ссылок</div>
                <div v-for="(link, i) in editForm.lesson_links" :key="i" class="link-row">
                  <input v-model="link.alias" placeholder="Название" class="link-alias" :disabled="saving" />
                  <input v-model="link.url" placeholder="https://..." class="link-url" :disabled="saving" />
                  <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать ссылку" @click="emit('link-remove', i)" :disabled="saving" aria-label="Убрать ссылку">−</button>
                </div>
                <div class="links-defaults">
                  <button type="button" class="btn btn--gry btn--xs" title="Взять из конфигурации ученика" :disabled="saving || !singleStudentId" @click="emit('links-from-config')">Из конфигурации</button>
                  <button type="button" class="btn btn--gry btn--xs" title="Взять из своих настроек" :disabled="saving" @click="emit('links-from-settings')">Из настроек</button>
                  <button type="button" class="btn btn--gry btn--xs" title="Сохранить в конфигурацию ученика" :disabled="saving || !singleStudentId" @click="emit('links-to-config')">В конфигурацию</button>
                  <button type="button" class="btn btn--gry btn--xs" title="Сохранить в свои настройки" :disabled="saving" @click="emit('links-to-settings')">В настройки</button>
                </div>
                <div v-if="!singleStudentId" class="pick-empty">Кнопки конфигурации доступны при одном участнике</div>
              </div>
              <div v-if="editErrors.start_time" class="ferr">{{ editErrors.start_time }}</div>
              <div v-if="editErrors.end_time" class="ferr">{{ editErrors.end_time }}</div>
              <div v-if="editMsg" class="fmsg fmsg--ok">{{ editMsg }}</div>
              <div v-if="editErr" class="fmsg fmsg--err">{{ editErr }}</div>
              <div class="info-actions">
                <button type="submit" class="btn btn--pri btn--sm" :disabled="saving">{{ saving ? '...' : 'Сохранить' }}</button>
                <button type="button" class="btn btn--gry btn--sm" @click="emit('cancel-edit')">Отмена</button>
              </div>
            </form>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// Левая колонка: просмотр и редактирование выбранных уроков.
// Данные — пропсами, намерения — эмитами. Форму правит напрямую
// (вложенные мутации объекта формы), структурные операции — эмиты.
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { fmtDateTime, lessonLinksVisible, lessonLinksRemainingMin, safeUrl } from '../../../logic/utils/index.js'
import { LESSON_STATUSES, MANUAL_LESSON_STATUSES } from '../../../logic/constants/index.js'
import { LessonNotes } from '../../components/index.js'

const props = defineProps({
  role: { type: String, default: '' },
  lessons: { type: Array, default: () => [] },
  selectedIds: { type: Object, default: () => new Set() },
  editingId: { type: [Number, String], default: null },
  editForm: { type: Object, default: () => ({}) },
  editErrors: { type: Object, default: () => ({}) },
  editMsg: { type: String, default: '' },
  editErr: { type: String, default: '' },
  participantsMap: { type: Object, default: () => ({}) },
  participantsLoading: { type: Object, default: () => ({}) },
  editRows: { type: Array, default: () => [] },
  addParticipantErr: { type: String, default: '' },
  students: { type: Array, default: () => [] },
  tutors: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits([
  'start-edit',
  'delete-lesson',
  'save-lesson',
  'cancel-edit',
  'row-add',
  'row-remove',
  'single-pick',
  'load-participants',
  'link-add',
  'link-remove',
  'links-from-config',
  'links-to-config',
  'links-from-settings',
  'links-to-settings',
  'confirm-request',
  'reject-request',
  'cancel-lesson',
])

// Единственный участник редактируемого урока (profile id) —
// только тогда доступны кнопки конфигурации (не для группы).
const singleStudentId = computed(() => {
  const list = props.editingId != null ? props.participantsMap[props.editingId] : null
  return Array.isArray(list) && list.length === 1 ? list[0].student_id : null
})

function studentName(userId) {
  const s = props.students.find((x) => x.user_id === userId)
  return s ? s.full_name : `#${userId}`
}

const selectedLessons = computed(() => props.lessons.filter((l) => props.selectedIds.has(l.lesson_id)))

// Видимость ссылок ученику: тикает каждые 30с, чтобы ссылки
// появлялись вовремя без перезагрузки. Репетитор видит всегда.
const nowTick = ref(0)
let tickTimer = 0
onMounted(() => {
  if (props.role === 'student') {
    tickTimer = setInterval(() => {
      nowTick.value = Date.now()
    }, 30000)
  }
})
onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer)
})

function visCfg(lesson) {
  return (props.tutors || []).find((t) => t.tutor_id === lesson.tutor_id) || null
}

function linksVisible(lesson) {
  void nowTick.value
  return lessonLinksVisible(visCfg(lesson), lesson.start_time)
}

function linksRemaining(lesson) {
  void nowTick.value
  return lessonLinksRemainingMin(visCfg(lesson), lesson.start_time)
}

function statusLabel(status) {
  return LESSON_STATUSES.find((s) => s.value === status)?.label || status || '—'
}

function rowOptions(rowKey) {
  const taken = new Set(
    props.editRows.filter((r) => r.key !== rowKey && r.student_user_id).map((r) => r.student_user_id),
  )
  return props.students.filter((s) => !taken.has(s.user_id))
}

const singleEditStudent = computed({
  get: () => (props.editRows.length ? props.editRows[0].student_user_id : null),
  set: (uid) => emit('single-pick', uid),
})
</script>

<style scoped>
.info-notes { margin-top: 10px; }
.info-actions--lesson { flex-wrap: wrap; }
/* Info block */
.side-block--info { display: flex; flex-direction: column; min-height: 0; }
.info-scroll {
  flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 10px;
  scrollbar-width: thin; scrollbar-color: var(--color-gray-400) var(--color-gray-100);
  direction: rtl;
}
.info-scroll > * { direction: ltr; }
.info-scroll::-webkit-scrollbar { width: 5px; }
.info-scroll::-webkit-scrollbar-track { background: var(--color-gray-100); border-radius: 3px; }
.info-scroll::-webkit-scrollbar-thumb { background: var(--color-gray-400); border-radius: 3px; }

.info-card {
  background: var(--color-gray-50); border-radius: 8px; padding: 12px; border: 1px solid var(--color-gray-200);
}
.info-card + .info-card { border-top: 2px solid var(--color-gray-300); }

.info-rows { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.info-r { display: flex; flex-direction: column; gap: 1px; }
/* .info-k/.info-actions/.part-chip — из base.css (single source). */
.link-list { display: flex; flex-direction: column; gap: 2px; }
.link-list a { font-size: 14px; }

/* Ссылки урока в редактировании */
.edit-links { display: flex; flex-direction: column; gap: 6px; margin: 8px 0; }
.link-row { display: flex; gap: 6px; align-items: flex-start; }
.link-alias { width: 110px; flex-shrink: 0; padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.link-url { flex: 1; min-width: 0; padding: 7px 10px; border: 1px solid var(--color-gray-300); border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.link-alias:focus, .link-url:focus { outline: none; border-color: var(--color-accent); }
.links-defaults { display: flex; flex-wrap: wrap; gap: 6px; }

.side-form { display: flex; flex-direction: column; gap: 8px; }

/* Participants */
.part-section { margin-bottom: 10px; }
.edit-participants { margin: 8px 0; }
.part-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
/* .part-empty/.part-chip — из base.css (single source). */
</style>
