<template>
  <div class="side-block">
    <h3 class="side-title">Информация</h3>
    <template v-if="!selected">
      <p class="side-hint">Выберите бронь для получения информации о ней</p>
    </template>
    <template v-else-if="!editing">
      <div v-if="deleteErr" class="fmsg fmsg--err">{{ deleteErr }}</div>
      <div v-if="updateMsg" class="fmsg fmsg--ok">{{ updateMsg }}</div>
      <div class="info-rows">
        <div class="info-r"><span class="info-k">День</span><span class="info-v">{{ weekdayLabels[selected.weekday] }}</span></div>
        <div class="info-r"><span class="info-k">Время</span><span class="info-v">{{ selected.start_time }} — {{ selected.end_time }}</span></div>
        <div class="info-r"><span class="info-k">Правило</span><span class="info-v">{{ RULE_LABELS[selected.access_rule] }}</span></div>
        <div v-if="selected.access_targets?.length" class="info-r">
          <span class="info-k">Ученики</span>
          <span class="info-v">{{ selected.access_targets.map(id => studentName(id)).join(', ') }}</span>
        </div>
      </div>
      <div class="info-actions">
        <button class="btn btn--pri btn--sm" @click="emit('start-edit')">Редактировать</button>
        <button class="btn btn--dan btn--sm" @click="emit('delete')" :disabled="saving">{{ saving ? '...' : 'Удалить' }}</button>
      </div>
    </template>
    <template v-else>
      <form class="side-form" @submit.prevent="emit('save')" novalidate>
        <label class="fl">День
          <select v-model="editForm.weekday">
            <option v-for="w in WEEKDAY_ORDER" :key="w" :value="w">{{ weekdayLabels[w] }}</option>
          </select>
        </label>
        <div class="frow">
          <label class="fl">Начало
            <input v-model="editForm.start_time" type="time" />
          </label>
          <label class="fl">Конец
            <input v-model="editForm.end_time" type="time" />
          </label>
        </div>
        <div class="rule-row">
          <label class="fl rule-select">Правило доступа
            <select v-model="editForm.access_rule">
              <option v-for="(l, r) in RULE_LABELS" :key="r" :value="r">{{ l }}</option>
            </select>
          </label>
          <button
            v-if="editForm.access_rule === 'ONLY' || editForm.access_rule === 'ALL_EXCEPT'"
            type="button" class="icon-btn icon-btn--add" @click="emit('open-picker')" title="Добавить ученика"
          >+</button>
        </div>
        <div v-if="editForm.access_rule === 'ONLY' || editForm.access_rule === 'ALL_EXCEPT'" class="targets">
          <div v-if="!students.length" class="pick-empty">Нет учеников</div>
          <div v-for="sid in editForm.access_targets" :key="sid" class="target-chip">
            <span>{{ studentName(sid) }}</span>
            <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" @click="emit('remove-target', sid)">−</button>
          </div>
        </div>
        <div v-if="editErrors.overlap" class="ferr">{{ editErrors.overlap }}</div>
        <div v-if="editMsg" class="fmsg fmsg--ok">{{ editMsg }}</div>
        <div v-if="editErr" class="fmsg fmsg--err">{{ editErr }}</div>
        <div class="info-actions">
          <button type="submit" class="btn btn--pri btn--sm" :disabled="saving">{{ saving ? '...' : 'Сохранить' }}</button>
          <button type="button" class="btn btn--gry btn--sm" @click="emit('cancel')">Отмена</button>
        </div>
      </form>
    </template>
  </div>
</template>

<script setup>
// Левая колонка: просмотр и редактирование выбранной брони.
// Форма правится напрямую (editForm — пропса), структурные намерения — эмиты.
import { WEEKDAY_ORDER, WEEKDAY_LABELS, RULE_LABELS } from '../../../logic/constants/index.js'

const props = defineProps({
  selected: { type: Object, default: null },
  editing: { type: Boolean, default: false },
  editForm: { type: Object, default: () => ({}) },
  editErrors: { type: Object, default: () => ({}) },
  editMsg: { type: String, default: '' },
  editErr: { type: String, default: '' },
  deleteErr: { type: String, default: '' },
  updateMsg: { type: String, default: '' },
  students: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['start-edit', 'delete', 'save', 'cancel', 'open-picker', 'remove-target'])

const weekdayLabels = WEEKDAY_LABELS

function studentName(sid) {
  const s = props.students.find((x) => x.student_id === sid)
  return s ? s.full_name : `#${sid}`
}
</script>

<style scoped>

/* === INFO === */
.info-rows { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.info-r { display: flex; flex-direction: column; gap: 1px; }
/* .info-k/.info-actions/.target-chip — из base.css (single source). */
.side-form { display: flex; flex-direction: column; gap: 10px; flex: 1; min-height: 0; }
/* === ACCESS TARGETS === */
.targets { display: flex; flex-wrap: wrap; gap: 6px; }
</style>
