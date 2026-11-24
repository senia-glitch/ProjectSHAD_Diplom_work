<template>
  <div class="side-block side-block--create">
    <div class="side-head">
      <h3 class="side-title">Новый урок</h3>
      <button v-if="slots.length" type="button" class="icon-btn icon-btn--add" title="Добавить форму урока" aria-label="Добавить форму урока" @click="addSlot"><UiIcon name="plus" /></button>
    </div>
    <div v-if="pickedIds.length" class="week-sum">
      <button type="button" class="week-toggle" @click="weekOpen = !weekOpen">
        <span>Окна недели ({{ weekTotal }})</span>
        <span>{{ weekOpen ? 'Скрыть' : 'Показать' }}</span>
      </button>
      <template v-if="weekOpen">
        <div v-for="row in weekSummary" :key="row.uid" class="week-row">
          <span
            class="week-dot"
            :style="{ background: row.colorId ? `var(--tutor-${row.colorId})` : 'var(--color-gray-300)' }"
          />
          <span class="week-txt"><span class="week-name">{{ row.name }}:</span>
            {{ row.lines.length ? row.lines.join(', ') : 'нет окон на открытой неделе — полистайте недели' }}</span>
        </div>
      </template>
    </div>
    <div v-if="weekErr" class="ferr">{{ weekErr }}</div>
    <div v-if="!slots.length" class="creator-empty">
      <p>Выберите репетитора и удобное время из доступных окон.</p>
      <button type="button" class="btn btn--pri btn--full" @click="addSlot"><UiIcon name="plus" />Записаться на урок</button>
    </div>
    <div v-else class="slots-scroll">
      <div v-for="(slot, i) in slots" :key="slot.key" class="slot">
        <div class="slot-head">
          <span class="slot-num">Форма {{ i + 1 }}</span>
          <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать форму" @click="removeSlot(i)" aria-label="Убрать форму">−</button>
        </div>
        <label class="fl">Репетитор
          <select v-model="slot.tutor_user_id" @change="onTutorChange(slot)">
            <option :value="null" disabled>Выберите репетитора</option>
            <option v-for="t in tutors" :key="t.tutor_user_id" :value="t.tutor_user_id">
              {{ t.full_name }} · шаг {{ t.slot_step_minutes }} мин
            </option>
          </select>
        </label>
        <div v-if="slot.tutor_user_id" class="color-row">
          <span class="pick-lbl">Цвет подсветки</span>
          <span class="color-dots">
            <button
              v-for="c in TUTOR_COLORS"
              :key="c.id"
              type="button"
              class="color-dot"
              :class="{ 'color-dot--active': tutorColors[slot.tutor_user_id] === c.id }"
              :style="{ background: `var(--tutor-${c.id})` }"
              :title="c.label"
              @click="emit('set-color', slot.tutor_user_id, c.id)"
            />
          </span>
        </div>
        <template v-if="slot.tutor_user_id">
          <div class="mode-row">
            <span class="pick-lbl">Режим</span>
            <label class="mode-opt"><input type="radio" :checked="slot.mode === 'weekly'" @change="slot.mode = 'weekly'" /> По дням недели</label>
            <label class="mode-opt"><input type="radio" :checked="slot.mode === 'dates'" @change="slot.mode = 'dates'" /> По дате</label>
            <button v-if="slot.mode === 'dates'" type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить дату" @click="addFormDate(slot)" aria-label="Добавить дату">+</button>
          </div>
          <StudentDateRows v-if="slot.mode === 'dates'" :slot="slot" :windows="windowsOf(slot)" :step="stepOf(slot)" />
          <StudentWeekRows v-else :slot="slot" :windows="windowsOf(slot)" :step="stepOf(slot)" />
          <div class="fl">
            <StudentLessonPreview
              :slot="slot"
              :windows="windowsOf(slot)"
              :step="stepOf(slot)"
              :loading="Boolean(slot._winLoading)"
            />
          </div>
          <div v-if="slot._winErr" class="ferr">{{ slot._winErr }}</div>
          <div v-if="slot.error" class="ferr">{{ slot.error }}</div>
          <div v-if="slot.ok" class="fmsg fmsg--ok">{{ slot.ok }}</div>
        </template>
        <div v-else class="pick-empty">Сначала выберите репетитора — подгрузятся его свободные окна</div>
      </div>
    </div>
    <div v-if="createGeneralErr" class="fmsg fmsg--err create-general">{{ createGeneralErr }}</div>
    <div v-if="slots.length" class="create-actions">
      <button type="button" class="btn btn--pri btn--full" :disabled="saving" @click="handleCreate">
        {{ saving ? '...' : 'Записаться' }}
      </button>
      <button type="button" class="icon-btn icon-btn--remove" title="Очистить форму" @click="emit('clear')" :disabled="saving" aria-label="Очистить форму">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18" /><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
// Правая колонка ученика: формы записи на уроки. Структура как у
// репетитора (режимы, предпросмотр, последовательное создание),
// вместо выбора ученика — выбор репетитора из связанных.
// Свободные окна грузятся под диапазон формы (кэш — в actions),
// на сетке подсвечиваются фоном. Ручные удаления из превью
// забываются при смене настроек формы (touch).
import { ref, watch, computed } from 'vue'
import { UiIcon } from '../../components/index.js'
import StudentDateRows from './StudentDateRows.vue'
import StudentWeekRows from './StudentWeekRows.vue'
import StudentLessonPreview from './StudentLessonPreview.vue'
import {
  loadStudentWindows,
  createStudentLessonsFromPreview,
  pruneStudentWindows,
} from '../../../logic/actions/index.js'
import { logInfo, logError } from '../../../logic/logger/index.js'
import {
  buildStudentPreview,
  slotRangeFromSlot,
  fmtPreview,
} from '../../../logic/utils/index.js'
import { WEEK_DAYS, SLOT_STEP_DEFAULT, TUTOR_COLORS } from '../../../logic/constants/index.js'
import { useScheduleStore } from '../../../logic/store/index.js'

const props = defineProps({
  slots: { type: Array, default: () => [] },
  tutors: { type: Array, default: () => [] },
  tutorColors: { type: Object, default: () => ({}) },
  weekRange: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['clear', 'update:saving', 'ensure-color', 'set-color'])

const createGeneralErr = ref('')
const weekErr = ref('')
const weekOpen = ref(false)
const windows = computed(() => useScheduleStore().uniqueStudentWindows)

const pickedIds = computed(() => [
  ...new Set(props.slots.map((s) => s.tutor_user_id).filter(Boolean)),
])

function tutorOf(uid) {
  return props.tutors.find((x) => x.tutor_user_id === uid)
}

const weekSummary = computed(() => {  const r = props.weekRange
  return pickedIds.value.map((uid) => {
    const lines = (windows.value || [])
      .filter(
        (w) =>
          w.tutorUserId === uid &&
          (!r?.dateFrom || (w.start.slice(0, 10) >= r.dateFrom && w.start.slice(0, 10) <= r.dateTo)),
      )
      .map((w) => fmtPreview(w.start, w.end))
    return {
      uid,
      name: tutorOf(uid)?.full_name || `#${uid}`,
      colorId: props.tutorColors[uid] || null,
      lines,
    }
  })
})

const weekTotal = computed(() => weekSummary.value.reduce((n, r) => n + r.lines.length, 0))

let slotSeq = 0
let rowSeq = 0

function newStudentSlot() {
  const weekdays = {}
  for (const d of WEEK_DAYS) weekdays[d.id] = { on: false, period: 1, startDate: '', count: 2, times: [] }
  return {
    key: ++slotSeq,
    mode: 'dates',
    dates: [],
    weekdays,
    tutor_user_id: null,
    dropped: [],
    _fp: '',
    _winKey: '',
    _winLoading: false,
    _winErr: '',
    error: '',
    ok: '',
  }
}

function addSlot() {
  props.slots.push(newStudentSlot())
}

function removeSlot(i) {
  props.slots.splice(i, 1)
  pruneStudentWindows(liveIds())
}

function liveIds() {
  return [...new Set(props.slots.map((s) => s.tutor_user_id).filter(Boolean))]
}

function addFormDate(slot) {
  slot.dates.push({ key: ++rowSeq, date: '', times: [] })
}

function stepOf(slot) {
  const t = props.tutors.find((x) => x.tutor_user_id === slot.tutor_user_id)
  return t?.slot_step_minutes > 0 ? t.slot_step_minutes : SLOT_STEP_DEFAULT
}

function windowsOf(slot) {
  if (!slot.tutor_user_id) return []
  return windows.value.filter((w) => w.tutorUserId === slot.tutor_user_id)
}

function fpOf(slot) {
  return JSON.stringify({
    t: slot.tutor_user_id,
    m: slot.mode,
    d: (slot.dates || []).map((x) => [
      x.date,
      (x.times || []).map((t) => [t.win, t.start, t.end, t.durKey]),
    ]),
    w: WEEK_DAYS.map((d) => {
      const c = slot.weekdays[d.id]
      return [c.on, c.period, c.startDate, c.count, c.times.map((t) => [t.start, t.durKey])]
    }),
  })
}

function touch(slot) {
  const fp = fpOf(slot)
  if (slot._fp !== fp) {
    slot._fp = fp
    slot.dropped = []
  }
}

async function fetchWindows(slot) {
  if (!slot.tutor_user_id) return
  const range = slotRangeFromSlot(slot)
  if (!range) return
  const key = `${slot.tutor_user_id}|${range.dateFrom}|${range.dateTo}`
  if (slot._winKey === key || slot._winLoading) return
  const t = props.tutors.find((x) => x.tutor_user_id === slot.tutor_user_id)
  slot._winLoading = true
  slot._winErr = ''
  try {
    await loadStudentWindows({
      tutorUserId: slot.tutor_user_id,
      tutorName: t?.full_name || '',
      dateFrom: range.dateFrom,
      dateTo: range.dateTo,
    })
    slot._winKey = key
  } catch (e) {
    if (!e.status) slot._winErr = 'Сеть'
    else slot._winErr = e.message || 'Не удалось загрузить окна'
    logError('schedule', 'studentWindows:fail', { error: e.message })
  } finally {
    slot._winLoading = false
  }
}

function onTutorChange(slot) {
  slot._winKey = ''
  slot.dropped = []
  if (slot.tutor_user_id) emit('ensure-color', slot.tutor_user_id)
  pruneStudentWindows(liveIds())
  fetchWindows(slot)
  fetchWeek(slot)
}

// Окна открытой недели — сразу на сетку, чтобы было видно,
// в какие дни есть время. Проверка идёт по диапазону формы.
async function fetchWeek(slot) {
  const r = props.weekRange
  if (!slot.tutor_user_id || !r?.dateFrom) return
  const t = props.tutors.find((x) => x.tutor_user_id === slot.tutor_user_id)
  try {
    await loadStudentWindows({
      tutorUserId: slot.tutor_user_id,
      tutorName: t?.full_name || '',
      dateFrom: r.dateFrom,
      dateTo: r.dateTo,
    })
    weekErr.value = ''
  } catch (e) {
    weekErr.value = 'Не удалось загрузить окна недели'
    logError('schedule', 'studentWeekWindows:fail', { error: e.message })
  }
}

let watchTimer = 0
watch(
  () => props.slots,
  () => {
    for (const s of props.slots) touch(s)
    clearTimeout(watchTimer)
    watchTimer = setTimeout(() => {
      for (const s of props.slots) fetchWindows(s)
    }, 600)
  },
  { deep: true },
)

async function handleCreate() {
  createGeneralErr.value = ''
  const plan = []
  for (const slot of props.slots) {
    slot.error = ''
    slot.ok = ''
    if (!slot.tutor_user_id) {
      slot.error = 'Выберите репетитора'
      continue
    }
    const { items } = buildStudentPreview(slot, windowsOf(slot), stepOf(slot))
    const valid = items.filter((x) => x.ok)
    const invalid = items.filter((x) => !x.ok)
    if (!valid.length) {
      slot.error = invalid.length
        ? `Нет уроков для записи — ${invalid.length} вне окон или не по шагу`
        : 'Нет уроков для записи — заполните даты и время'
      continue
    }
    plan.push({ slot, valid, invalidCount: invalid.length })
  }
  if (!plan.length) {
    if (!createGeneralErr.value) createGeneralErr.value = 'Нет уроков для записи'
    return
  }
  emit('update:saving', true)
  const allFailures = []
  try {
    for (const { slot, valid, invalidCount } of plan) {
      const { created, lessonIds, failed } = await createStudentLessonsFromPreview(valid, {
        tutorUserId: slot.tutor_user_id,
      })
      for (const lessonId of lessonIds) logInfo('schedule', 'studentCreate:ok', { lesson_id: lessonId })
      const failures = failed.map(
        (f) => `${fmtPreview(f.start, f.end)}: ${f.message || 'Ошибка'}`,
      )
      for (const f of failed) logError('schedule', 'studentCreate:fail', { start: f.start, error: f.message })
      const parts = [`Создано уроков: ${created}`]
      if (invalidCount) parts.push(`пропущено вне окон: ${invalidCount}`)
      if (failures.length) {
        slot.error = `${parts.join(', ')}: ${failures.join('; ')}`
        allFailures.push(...failures)
      } else {
        slot.ok = parts.join(', ')
      }
    }
  } catch (e) {
    createGeneralErr.value = 'Сеть'
    logError('schedule', 'studentCreate:networkError', { error: e.message })
    return
  } finally {
    emit('update:saving', false)
  }
  if (allFailures.length) {
    createGeneralErr.value = `Не создано: ${allFailures.join('; ')}`
  }
  emit('clear')
}
</script>

<style scoped>
.side-block--create { flex-direction: column; display: flex; }
.create-general { margin-top: 8px; }
.side-block--create .btn--full { flex-shrink: 0; }
/* Ряд действий под формами: "Записаться" тянется, корзина справа. */
.create-actions { display: flex; gap: 8px; }
.create-actions .btn--full { width: auto; flex: 1; }
.slot {
  background: var(--color-gray-50); border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 8px;
  border: 1px solid var(--color-gray-200);
}
.slot-head { display: flex; align-items: center; justify-content: space-between; }
.slot-num { font-size: 12px; font-weight: 600; color: var(--color-gray-700); }
/* Сводка окон открытой недели: что подсвечено на сетке прямо сейчас. */
.week-sum {
  display: flex; flex-direction: column; gap: 4px; padding: 10px;
  background: var(--color-gray-50); border: 1px solid var(--color-gray-200); border-radius: 8px;
}
.week-toggle {
  display: flex; align-items: center; justify-content: space-between; width: 100%;
  background: none; border: none; cursor: pointer; padding: 0;
  font-size: 12px; font-weight: 600; color: var(--color-gray-700);
}
.week-row { display: flex; align-items: flex-start; gap: 6px; font-size: 12px; color: var(--color-gray-700); }
.week-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; }
.week-name { font-weight: 600; }
/* Выбор цвета подсветки окон репетитора (один цвет на репетитора). */
.color-row { display: flex; align-items: center; gap: 8px; }
.color-row .pick-lbl { margin: 0; }
.color-dots { display: flex; flex-wrap: wrap; gap: 6px; }
.color-dot {
  width: 22px; height: 22px; border-radius: 50%; cursor: pointer;
  border: 2px solid var(--color-gray-300); padding: 0; transition: transform 150ms;
}
.color-dot--active { border-color: var(--color-accent); transform: scale(1.15); }
.mode-row { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; color: var(--color-gray-700); }
.mode-opt { display: flex; align-items: center; gap: 6px; cursor: pointer; font-weight: 500; }
.mode-opt input { width: auto; }
</style>
