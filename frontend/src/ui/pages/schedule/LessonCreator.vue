<template>
  <div class="side-block side-block--create">
    <div class="side-head">
      <h3 class="side-title">Создать урок</h3>
      <button v-if="slots.length" type="button" class="icon-btn icon-btn--add" title="Добавить форму урока" aria-label="Добавить форму урока" @click="addSlot"><UiIcon name="plus" /></button>
    </div>
    <div v-if="!slots.length" class="creator-empty">
      <p>Выберите дату, время и ученика. Урок появится в вашем расписании.</p>
      <button type="button" class="btn btn--pri btn--full" @click="addSlot"><UiIcon name="plus" />Добавить урок</button>
    </div>
    <div v-else class="slots-scroll">
      <div v-for="(slot, i) in slots" :key="slot.key" class="slot">
        <div class="slot-head">
          <span class="slot-num">Форма {{ i + 1 }}</span>
                  <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать форму" @click="removeSlot(i)" aria-label="Убрать форму">−</button>
        </div>
                <div class="mode-row">
                  <span class="pick-lbl">Режим</span>
                  <label class="mode-opt"><input type="radio" :checked="slot.mode === 'weekly'" @change="slot.mode = 'weekly'" /> По дням недели</label>
                  <label class="mode-opt"><input type="radio" :checked="slot.mode === 'dates'" @change="slot.mode = 'dates'" /> По дате</label>
                  <button v-if="slot.mode === 'dates'" type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить дату" @click="addFormDate(slot)" aria-label="Добавить дату">+</button>
                </div>
        <DateTimesEditor v-if="slot.mode === 'dates'" :slot="slot" />
        <WeekdaysEditor v-else :slot="slot" />
        <!-- === Ученики: либо один на все уроки, либо строки при групповом === -->
        <div class="group-row">
          <label class="fl checkbox-label group-check">
            <input type="checkbox" v-model="slot.is_group" /> Групповой
          </label>
          <button
            v-if="slot.is_group" type="button"
            class="icon-btn icon-btn--xs icon-btn--add"
            title="Добавить ученика" @click="addGroupRow(slot)"
           aria-label="Добавить ученика">+</button>
        </div>
        <template v-if="slot.is_group">
          <div v-if="!slot.groupRows.length" class="pick-empty">Нажмите + возле «Групповой», чтобы добавить учеников</div>
          <div v-for="row in slot.groupRows" :key="row.key" class="add-part">
            <select v-model="row.user_id" class="add-part-select">
              <option :value="null" disabled>Выберите ученика</option>
              <option v-for="s in slotGroupOptions(slot, row.key)" :key="s.user_id" :value="s.user_id">{{ s.full_name }}</option>
            </select>
            <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать" @click="removeGroupRow(slot, row.key)" aria-label="Убрать">−</button>
          </div>
        </template>
        <label v-else class="inline-field"><span>Ученик (на все уроки)</span>
          <select v-model="slot.student_user_id">
            <option :value="null">— Без ученика —</option>
            <option v-for="s in students" :key="s.user_id" :value="s.user_id">{{ s.full_name }}</option>
          </select>
        </label>
        <div class="fl">
          <LessonPreview :slot="slot" />
        </div>
        <div v-if="slot.error" class="ferr">{{ slot.error }}</div>
        <div v-if="slot.ok" class="fmsg fmsg--ok">{{ slot.ok }}</div>
      </div>
    </div>
    <div v-if="createGeneralErr" class="fmsg fmsg--err" style="margin-top:8px">{{ createGeneralErr }}</div>
    <div v-if="slots.length" class="create-actions">
      <button type="button" class="btn btn--pri btn--full" :disabled="saving" @click="handleCreate">
        {{ saving ? '...' : 'Создать' }}
      </button>
      <button type="button" class="icon-btn icon-btn--remove" title="Очистить форму" @click="emit('clear')" :disabled="saving" aria-label="Очистить форму">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18" /><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
// Правая колонка: формы создания уроков. Вложенные мутации слотов —
// прямо здесь (слот — пропса, заменяется только массив целиком через
// слот-эмиты выше). Создание — через actions, превью — через utils.
import { ref, watch } from 'vue'
import { UiIcon } from '../../components/index.js'
import DateTimesEditor from './DateTimesEditor.vue'
import WeekdaysEditor from './WeekdaysEditor.vue'
import LessonPreview from './LessonPreview.vue'
import { createLessonsFromPreview } from '../../../logic/actions/index.js'
import { logInfo, logError } from '../../../logic/logger/index.js'
import { fpOf, previewItems, fmtPreview } from '../../../logic/utils/index.js'
import { WEEK_DAYS } from '../../../logic/constants/index.js'

const props = defineProps({
  slots: { type: Array, default: () => [] },
  students: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['clear', 'update:saving'])

const createGeneralErr = ref('')

let rowSeq = 0
let slotSeq = 0

function newSlot() {
  const weekdays = {}
  for (const d of WEEK_DAYS) weekdays[d.id] = { on: false, period: 1, startDate: '', count: 4, times: [] }
  return {
    key: ++slotSeq,
    mode: 'dates',
    dates: [],
    weekdays,
    student_user_id: null,
    is_group: false,
    groupRows: [],
    dropped: [],
    _fp: '',
    error: '',
    ok: '',
  }
}

function addSlot() {
  props.slots.push(newSlot())
}

function removeSlot(i) {
  props.slots.splice(i, 1)
}

function addFormDate(slot) {
  slot.dates.push({ key: ++rowSeq, date: '', times: [] })
}

function addGroupRow(slot) {
  slot.groupRows.push({ key: ++rowSeq, user_id: null })
}

function removeGroupRow(slot, rowKey) {
  slot.groupRows = slot.groupRows.filter((r) => r.key !== rowKey)
}

function slotGroupOptions(slot, rowKey) {
  const taken = new Set(
    slot.groupRows.filter((r) => r.key !== rowKey && r.user_id).map((r) => r.user_id),
  )
  return props.students.filter((s) => !taken.has(s.user_id))
}

// Ручные удаления из превью забываются при смене настроек формы.
function touch(slot) {
  const fp = fpOf(slot)
  if (slot._fp !== fp) {
    slot._fp = fp
    slot.dropped = []
  }
}

watch(
  () => props.slots,
  () => {
    for (const s of props.slots) touch(s)
  },
  { deep: true },
)

function participantIdsOf(slot) {
  if (!slot.is_group) return slot.student_user_id ? [slot.student_user_id] : []
  return [...new Set(slot.groupRows.filter((r) => r.user_id).map((r) => r.user_id))]
}

async function handleCreate() {
  createGeneralErr.value = ''
  const plan = []
  for (const slot of props.slots) {
    slot.error = ''
    slot.ok = ''
    const items = previewItems(slot)
    if (items.length) plan.push({ slot, items })
  }
  if (!plan.length) {
    createGeneralErr.value = 'Нет уроков для создания — заполните даты и время'
    return
  }

  emit('update:saving', true)
  const allFailures = []
  try {
    for (const { slot, items } of plan) {
      const { created, lessonIds, failed } = await createLessonsFromPreview(items, {
        isGroup: slot.is_group,
        participantIds: participantIdsOf(slot),
      })
      for (const lessonId of lessonIds) logInfo('schedule', 'create:ok', { lesson_id: lessonId })
      const failures = failed.map((f) => {
        if (f.kind === 'participant' && !f.network) {
          return `урок создан, ученик — ${f.payload?.error?.message || 'Ошибка'}`
        }
        return `${fmtPreview(f.start, f.end)}: ${f.network ? f.message : f.payload?.error?.message || 'Ошибка'}`
      })
      for (const f of failed) logError('schedule', 'create:fail', { start: f.start, error: f.message })
      if (failures.length) {
        slot.error = `Создано ${created} из ${items.length}: ${failures.join('; ')}`
        allFailures.push(...failures)
      } else {
        slot.ok = `Создано уроков: ${created}`
      }
    }
  } catch (e) {
    createGeneralErr.value = 'Сеть'
    logError('schedule', 'create:networkError', { error: e.message })
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
.side-block--create .btn--full { flex-shrink: 0; }
/* Ряд действий под формами: "Создать" тянется, корзина справа. */
.create-actions { display: flex; gap: 8px; }
.create-actions .btn--full { width: auto; flex: 1; }
.slot {
  background: var(--color-gray-50); border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 8px;
  border: 1px solid var(--color-gray-200);
}
.slot-head { display: flex; align-items: center; justify-content: space-between; }
.slot-num { font-size: 12px; font-weight: 600; color: var(--color-gray-700); }
.mode-row { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; color: var(--color-gray-700); }
.mode-opt { display: flex; align-items: center; gap: 6px; cursor: pointer; font-weight: 500; }
.mode-opt input { width: auto; }
/* Чекбокс "Групповой" и "+" добавления ученика — в одну строку. */
.group-row { display: flex; align-items: center; gap: 8px; }
.group-check { flex: 1; }
</style>
