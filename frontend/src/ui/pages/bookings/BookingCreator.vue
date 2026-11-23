<template>
  <div class="side-block">
    <div class="side-head">
      <h3 class="side-title">Создать бронь</h3>
      <button type="button" class="icon-btn icon-btn--add" @click="addSlot" title="Добавить слот">+</button>
    </div>
    <form class="create-form" @submit.prevent="handleCreate" novalidate>
      <div class="slots-scroll">
        <div v-for="(slot, si) in slots" :key="si" class="slot">
          <div class="slot-head">
            <span class="slot-label">Бронь</span>
            <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" @click="removeSlot(si)" title="Удалить слот">−</button>
          </div>
          <label class="fl">День
            <select v-model="slot.weekday">
              <option v-for="w in WEEKDAY_ORDER" :key="w" :value="w">{{ weekdayLabels[w] }}</option>
            </select>
          </label>
          <div class="frow">
            <label class="fl">Начало
              <input v-model="slot.start_time" type="time" />
            </label>
            <label class="fl">Конец
              <input v-model="slot.end_time" type="time" />
            </label>
          </div>
          <div class="rule-row">
            <label class="fl rule-select">Правило доступа
              <select v-model="slot.access_rule">
                <option v-for="(l, r) in RULE_LABELS" :key="r" :value="r">{{ l }}</option>
              </select>
            </label>
            <button
              v-if="slot.access_rule === 'ONLY' || slot.access_rule === 'ALL_EXCEPT'"
              type="button" class="icon-btn icon-btn--add" @click="emit('pick-student', si)" title="Добавить ученика"
            >+</button>
          </div>
          <div v-if="slot.access_rule === 'ONLY' || slot.access_rule === 'ALL_EXCEPT'" class="targets">
            <div v-if="!students.length" class="pick-empty">Нет учеников</div>
            <div v-for="sid in slot.access_targets" :key="sid" class="target-chip">
              <span>{{ studentName(sid) }}</span>
              <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" @click="removeTarget(si, sid)">−</button>
            </div>
          </div>
          <div v-if="slotErrors[si]" class="ferr">{{ slotErrors[si] }}</div>
        </div>
      </div>

      <div class="fl">
        <span class="pick-lbl">Предпросмотр ({{ slots.length }})</span>
        <div v-for="(slot, si) in slots" :key="si" class="pv-row">
          <span>{{ fmtSlot(slot) }}</span>
          <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать из списка" @click="removeSlot(si)">−</button>
        </div>
      </div>

      <div v-if="overlapErr" class="ferr">{{ overlapErr }}</div>
      <div v-if="createMsg" class="fmsg fmsg--ok">{{ createMsg }}</div>
      <div v-if="createErr" class="fmsg fmsg--err">{{ createErr }}</div>
      <div v-if="!slots.length" class="pick-empty">Нажмите на знак + чтобы добавить бронь</div>
      <div v-else class="create-actions">
        <button type="submit" class="btn btn--pri btn--full" :disabled="saving">{{ saving ? '...' : 'Создать' }}</button>
        <button type="button" class="icon-btn icon-btn--remove" title="Очистить форму" @click="clearCreateForm" :disabled="saving">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18" /><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /></svg>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
// Правая колонка: формы создания броней. Слоты — вложенные мутации
// пропсы (структурных замен массива нет), валидация и создание — здесь.
import { ref, reactive, watch } from 'vue'
import { createBookings } from '../../../logic/actions/index.js'
import { logInfo, logError } from '../../../logic/logger/index.js'
import { WEEKDAY_ORDER, WEEKDAY_LABELS, WEEKDAY_SHORT, RULE_LABELS, ruleRequiresTargets } from '../../../logic/constants/index.js'
import { toMin, hasOverlap } from '../../../logic/utils/index.js'

const props = defineProps({
  slots: { type: Array, default: () => [] },
  students: { type: Array, default: () => [] },
  bookings: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['pick-student', 'update:saving'])

const weekdayLabels = WEEKDAY_LABELS

const slotErrors = reactive({})
const overlapErr = ref('')
const createMsg = ref('')
const createErr = ref('')

function studentName(sid) {
  const s = props.students.find((x) => x.student_id === sid)
  return s ? s.full_name : `#${sid}`
}

function fmtSlot(slot) {
  const day = WEEKDAY_SHORT[slot.weekday] || slot.weekday
  const time = `${String(slot.start_time || '').slice(0, 5)}–${String(slot.end_time || '').slice(0, 5)}`
  let rule = RULE_LABELS[slot.access_rule] || slot.access_rule
  if (ruleRequiresTargets(slot.access_rule) && slot.access_targets?.length) {
    rule += ` (${slot.access_targets.length})`
  }
  return `${day} ${time} · ${rule}`
}

function addSlot() {
  props.slots.push({
    weekday: 'MONDAY',
    start_time: '09:00',
    end_time: '10:00',
    access_rule: 'EVERYONE',
    access_targets: [],
  })
}

function removeSlot(idx) {
  props.slots.splice(idx, 1)
}

function clearCreateForm() {
  props.slots.splice(0, props.slots.length)
  clearErrors()
}

function removeTarget(slotIndex, studentId) {
  const targets = props.slots[slotIndex].access_targets
  const idx = targets.indexOf(studentId)
  if (idx !== -1) targets.splice(idx, 1)
}

function clearErrors() {
  Object.keys(slotErrors).forEach((k) => delete slotErrors[k])
  overlapErr.value = ''
  createMsg.value = ''
  createErr.value = ''
}

defineExpose({ clearErrors })

// Структурные изменения слотов инвалидируют ошибки слотов.
// Сообщения (успех/общая ошибка) не трогаем — ими управляет создание.
watch(
  () => props.slots.length,
  () => {
    Object.keys(slotErrors).forEach((k) => delete slotErrors[k])
    overlapErr.value = ''
  },
)

function validateSlot(slot, excludeId) {
  let err = ''
  if (slot.start_time && slot.end_time && toMin(slot.start_time) >= toMin(slot.end_time)) {
    err = 'Конец должен быть позже начала'
  } else if (
    slot.start_time &&
    slot.end_time &&
    hasOverlap(props.bookings, slot.weekday, slot.start_time, slot.end_time, excludeId)
  ) {
    err = 'Пересечение'
  } else if (ruleRequiresTargets(slot.access_rule) && !slot.access_targets?.length) {
    err = 'Добавьте учеников'
  }
  return err
}

function validateAll() {
  clearErrors()
  let ok = true
  props.slots.forEach((slot, i) => {
    const err = validateSlot(slot)
    if (err) {
      slotErrors[i] = err
      ok = false
    } else {
      delete slotErrors[i]
    }
  })
  return ok
}

async function handleCreate() {
  logInfo('bookings', 'create:submit', { slots: props.slots.map((s) => ({ ...s })) })
  if (!validateAll()) {
    logInfo('bookings', 'create:validationFailed', { errors: { ...slotErrors } })
    return
  }
  emit('update:saving', true)
  try {
    const { created, items, error } = await createBookings(props.slots)
    items.forEach((mapped, i) => logInfo('bookings', `create:ok [${i}]`, { result: mapped }))
    if (error) {
      createErr.value = error.message || `Ошибка в слоте ${error.slotIndex + 1}`
      logError('bookings', `create:fail [${error.slotIndex}]`, {
        status: error.status,
        error: error.payload?.error,
      })
    }
    if (created > 0) {
      props.slots.splice(0, props.slots.length)
      Object.keys(slotErrors).forEach((k) => delete slotErrors[k])
      overlapErr.value = ''
      createErr.value = ''
      createMsg.value = `Создано: ${created}`
      setTimeout(() => (createMsg.value = ''), 3000)
    }
  } catch (e) {
    createErr.value = 'Сеть'
    logError('bookings', 'create:networkError', { error: e.message })
  } finally {
    emit('update:saving', false)
  }
}
</script>

<style scoped>
.slots-scroll { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; gap: 10px; }
.slots-scroll::-webkit-scrollbar { width: 6px; }
.slots-scroll::-webkit-scrollbar-track { background: var(--color-gray-100); border-radius: 3px; }
.slots-scroll::-webkit-scrollbar-thumb { background: var(--color-gray-400); border-radius: 3px; }
.slots-scroll::-webkit-scrollbar-thumb:hover { background: var(--color-gray-500); }

.create-form { display: flex; flex-direction: column; gap: 10px; flex: 1; min-height: 0; }
/* Ряд действий под формами: "Создать" тянется, корзина справа. */
.create-actions { display: flex; gap: 8px; }
.create-actions .btn--full { width: auto; flex: 1; }

/* === SLOT (nested form) === */
.slot {
  border-top: 3px solid var(--slot-separator); padding-top: 10px; display: flex; flex-direction: column; gap: 10px;
  background: var(--color-gray-50); margin: 0 -16px; padding: 12px 16px 10px;
}
.slot:first-child { border-top: none; margin-top: 0; padding-top: 0; }
.slot:last-child { margin-bottom: 0; }
.slot-head { display: flex; align-items: center; justify-content: space-between; }
.slot-label { font-size: 12px; font-weight: 600; color: var(--color-gray-700); }

/* Правило — потомок слота, ученики — потомки правила: лесенка отступов
   показывает вложенность, как .nest в расписании. */
.slot .rule-row { margin-right: 8px; }
.slot .targets { margin-left: 10px; padding-left: 8px; border-left: 2px solid var(--color-gray-200); }

/* === ACCESS TARGETS === */
.targets { display: flex; flex-wrap: wrap; gap: 6px; }
/* .target-chip — из base.css (single source). */
</style>
