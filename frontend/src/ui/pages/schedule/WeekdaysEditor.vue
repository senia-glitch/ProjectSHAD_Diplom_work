<template>
  <div class="wd-row">
    <label v-for="wd in WEEK_DAYS" :key="wd.id" class="wd-check" :title="wd.full">
      <span>{{ wd.short }}</span>
      <input type="checkbox" :checked="slot.weekdays[wd.id].on" @change="toggleWeekday(wd.id)" />
    </label>
  </div>
  <template v-for="wd in WEEK_DAYS" :key="wd.id">
    <div v-if="slot.weekdays[wd.id].on" class="day-card">
      <div class="day-head">
        <span class="day-title">{{ wd.full }}</span>
        <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать день" @click="toggleWeekday(wd.id)">−</button>
      </div>
      <label class="fl"><span class="info-k">Начать с</span>
        <input v-model="slot.weekdays[wd.id].startDate" type="date" />
      </label>
      <div v-if="!slot.weekdays[wd.id].startDate" class="pick-empty">Заполни дату первой для отсчёта недели</div>
      <div class="frow">
        <label class="fl"><span class="info-k">Повтор</span>
          <select v-model.number="slot.weekdays[wd.id].period">
            <option v-for="n in 12" :key="n" :value="n">{{ n === 1 ? 'каждую неделю' : `раз в ${n} ${periodWord(n)}` }}</option>
          </select>
        </label>
        <label class="fl"><span class="info-k">Всего занятий</span>
          <input v-model.number="slot.weekdays[wd.id].count" type="number" min="1" max="500" />
        </label>
      </div>
      <div class="add-part">
        <span class="info-k">Время занятия</span>
        <button type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить время" @click="addDayTime(wd.id)">+</button>
      </div>
      <div v-for="t in slot.weekdays[wd.id].times" :key="t.key" class="add-part add-part--sub">
        <input v-model="t.start" type="time" class="time-in" />
        <input v-model="t.end" type="time" class="time-in" />
        <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать время" @click="removeDayTime(wd.id, t.key)">−</button>
      </div>
      <div v-if="dayDates(wd.id).length" class="day-dates">
        <span class="info-k">Даты</span>
        <span>{{ dayDates(wd.id).slice(0, 6).map(shortDate).join(' · ') }}<span v-if="dayDates(wd.id).length > 6"> …</span></span>
      </div>
    </div>
  </template>
</template>

<script setup>
// Редактор режима «по дням недели» одной формы. Всё — вложенные мутации
// объекта слота, поэтому эмитов нет. Чистые справочники — из contracts.
import { WEEK_DAYS } from '../../../logic/constants/index.js'
import { periodWord, nearestWeekday, fmtDate } from '../../../logic/utils/index.js'

const props = defineProps({
  slot: { type: Object, required: true },
})

let rowSeq = 0

function blankTime() {
  return { key: ++rowSeq, start: '', end: '' }
}

function toggleWeekday(dayId) {
  const cfg = props.slot.weekdays[dayId]
  cfg.on = !cfg.on
  if (cfg.on) {
    if (!cfg.startDate) {
      const jsDay = (WEEK_DAYS.findIndex((d) => d.id === dayId) + 1) % 7
      cfg.startDate = nearestWeekday(jsDay)
    }
    cfg.count = cfg.count || 4
    cfg.times = cfg.times?.length ? cfg.times : [blankTime()]
  } else {
    cfg.times = []
  }
}

function addDayTime(dayId) {
  props.slot.weekdays[dayId].times.push(blankTime())
}

function removeDayTime(dayId, timeKey) {
  const cfg = props.slot.weekdays[dayId]
  cfg.times = cfg.times.filter((t) => t.key !== timeKey)
}

// Даты правила дня для мини-превью: от недели старта, не больше кол-ва.
function dayDates(dayId) {
  const cfg = props.slot.weekdays?.[dayId]
  if (!cfg?.startDate) return []
  const k = Math.max(0, Math.floor(Number(cfg.count)) || 0)
  if (k < 1) return []
  const jsDay = (WEEK_DAYS.findIndex((d) => d.id === dayId) + 1) % 7
  const out = []
  const base = new Date(`${cfg.startDate}T00:00`)
  if (Number.isNaN(base.getTime())) return []
  const monday = new Date(base)
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
  const period = Math.max(1, Math.floor(Number(cfg.period)) || 1)
  const off = (jsDay + 6) % 7
  for (let w = 0; w < 500 && out.length < k; w++) {
    if (w % period !== 0) continue
    const date = new Date(monday)
    date.setDate(date.getDate() + w * 7 + off)
    const ds = fmtDate(date)
    if (ds >= cfg.startDate) out.push(ds)
  }
  return out
}

function shortDate(ds) {
  const [, M, D] = ds.split('-')
  return `${D}.${M}`
}
</script>

<style scoped>
/* Дни недели: чекбоксы в ряд, сокращённое название над каждым. */
.wd-row { display: flex; gap: 2px; }
.wd-check { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 11px; color: var(--color-gray-700); cursor: pointer; }
.wd-check input { width: auto; margin: 0; }
</style>
