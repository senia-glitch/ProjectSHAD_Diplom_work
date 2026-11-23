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
        <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать день" @click="toggleWeekday(wd.id)" aria-label="Убрать день">−</button>
      </div>
      <label class="fl"><span class="info-k">Начать с</span>
        <input v-model="slot.weekdays[wd.id].startDate" type="date" />
      </label>
      <div v-if="!slot.weekdays[wd.id].startDate" class="pick-empty">Заполни дату первой для отсчёта недели, уроки будут начинаться с этой недели (дата указывает на неделю как ориентир)</div>
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
      <div class="pick-empty">Заполни кол-во уроков, начиная с указанной ранее недели добавится именно указанное кол-во</div>
      <template v-if="hasWindows(wd.id)">
        <div class="add-part">
          <span class="info-k">Время занятия</span>
          <button type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить время" @click="addDayTime(wd.id)" aria-label="Добавить время">+</button>
        </div>
        <div v-for="t in slot.weekdays[wd.id].times" :key="t.key" class="add-part add-part--sub">
        <select v-model="t.start" class="time-in" @change="onStart(wd.id, t.key)">
          <option :value="''" disabled>Старт</option>
          <option v-for="s in startOptions(wd.id)" :key="s" :value="s">{{ s }}</option>
        </select>
        <select v-model="t.durKey" class="time-in" @change="onDuration(wd.id, t.key)">
          <option :value="''" disabled>Длительность</option>
          <option v-for="o in durationOptions(wd.id, t)" :key="o.key" :value="o.key">{{ o.label }}</option>
        </select>
          <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать время" @click="removeDayTime(wd.id, t.key)" aria-label="Убрать время">−</button>
        </div>
      </template>
      <div v-else class="pick-empty">Свободных окон нет — выбери другой день</div>
      <div v-if="dayDates(wd.id).length" class="day-dates">
        <span class="info-k">Даты</span>
        <span>{{ dayDates(wd.id).slice(0, 6).map(shortDate).join(' · ') }}<span v-if="dayDates(wd.id).length > 6"> …</span></span>
      </div>
    </div>
  </template>
  <div v-if="!genActive" class="pick-empty">Отметь дни недели — у каждого появятся своя дата отсчёта, кол-во и время и жирный пунктир таблице на этом дне</div>
</template>

<script setup>
// Редактор режима «по дням недели» формы ученика: один день — одна
// карточка. Порядок: день → правило («Начать с», «Повтор»,
// «Всего занятий») → время → мини-превью дат. Даты скрыты:
// при отметке дня дата подставляется ближайшим вхождением.
// Сетка стартов строится из окон первой даты дня; каждая дата
// при развёртке проверяется по своим окнам (мимо — пропуск с причиной).
// Вложенные мутации объекта слота, поэтому эмитов нет.
import { computed } from 'vue'
import { WEEK_DAYS } from '../../../logic/constants/index.js'
import {
  periodWord,
  fmtDur,
  generateWeeklyDates,
  buildStartGrid,
  buildDurations,
  toHHMM,
  toMinutesOfDay,
} from '../../../logic/utils/index.js'

const props = defineProps({
  slot: { type: Object, required: true },
  windows: { type: Array, default: () => [] },
  step: { type: Number, default: 60 },
})

let rowSeq = 0

const genActive = computed(() => WEEK_DAYS.some((d) => props.slot.weekdays[d.id]?.on))

function blankTime() {
  return { key: ++rowSeq, start: '', durKey: '', durationMin: null, durationKind: '' }
}

function toggleWeekday(dayId) {
  const cfg = props.slot.weekdays[dayId]
  cfg.on = !cfg.on
  if (cfg.on) {
    if (!cfg.startDate) cfg.startDate = nearestDate(dayId)
    cfg.count = cfg.count || 2
    cfg.times = cfg.times?.length ? cfg.times : [blankTime()]
  } else {
    cfg.times = []
  }
}

// Ближайшее вхождение дня недели (включая сегодня): человек думает
// «начать с 23.09», система понимает «отсчёт от недели 23.09».
function nearestDate(dayId) {
  const jsDay = (WEEK_DAYS.findIndex((d) => d.id === dayId) + 1) % 7
  const t = new Date()
  t.setHours(0, 0, 0, 0)
  const d = new Date(t)
  d.setDate(d.getDate() + ((jsDay - d.getDay() + 7) % 7))
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

// Даты правила для мини-превью: от недели старта, не больше кол-ва.
function dayDates(dayId) {
  const cfg = props.slot.weekdays[dayId]
  if (!cfg?.startDate) return []
  const k = Math.max(0, Math.floor(Number(cfg.count)) || 0)
  if (k < 1) return []
  const all = generateWeeklyDates(
    { weekdays: { [dayId]: { on: true, period: cfg.period } }, startDate: cfg.startDate },
    500,
  ).filter((ds) => ds >= cfg.startDate)
  return all.slice(0, k)
}

function shortDate(ds) {
  const [, M, D] = ds.split('-')
  return `${D}.${M}`
}

function addDayTime(dayId) {
  props.slot.weekdays[dayId].times.push(blankTime())
}

function removeDayTime(dayId, timeKey) {
  const cfg = props.slot.weekdays[dayId]
  cfg.times = cfg.times.filter((t) => t.key !== timeKey)
}

// Первая дата правила для дня недели: от её недели идёт отсчёт,
// из её окон строится сетка стартов.
function firstDateOf(dayId) {
  const cfg = props.slot.weekdays[dayId]
  if (!cfg?.startDate) return ''
  const jsDay = (WEEK_DAYS.findIndex((d) => d.id === dayId) + 1) % 7
  const probe = {}
  for (const d of WEEK_DAYS) {
    probe[d.id] = d.id === dayId
      ? { on: true, period: cfg.period }
      : { on: false, period: 1 }
  }
  const all = generateWeeklyDates({ weekdays: probe, startDate: cfg.startDate }, 400)
  return all.find((ds) => ds >= cfg.startDate && new Date(`${ds}T00:00`).getDay() === jsDay) || ''
}

function firstDateWindows(dayId) {
  const ds = firstDateOf(dayId)
  if (!ds) return []
  return props.windows.filter((w) => w.start.slice(0, 10) === ds)
}

// Есть ли известное свободное время: окна первой даты дня загружены
// и непусты. Без даты — тоже нет (скрываем время и кол-во).
function hasWindows(dayId) {
  return firstDateWindows(dayId).length > 0
}

function startOptions(dayId) {
  if (!props.slot.weekdays[dayId]?.startDate) return []
  const ws = firstDateWindows(dayId)
  if (!ws.length) {
    const st = props.step > 0 ? props.step : 60
    const out = []
    for (let m = 0; m < 24 * 60; m += st) out.push(toHHMM(m))
    return out
  }
  const set = new Set()
  for (const w of ws) {
    const s = toMinutesOfDay(w.start.slice(11, 16))
    const e = toMinutesOfDay(w.end.slice(11, 16))
    for (const m of buildStartGrid(s, e, props.step)) set.add(toHHMM(m))
  }
  return [...set].sort()
}

function durationOptions(dayId, t) {
  // Остаток слота от выбранного старта по окну первой даты:
  // больше остатка не предлагаем. Без старта или вне окон —
  // полный список, точную проверку даст предпросмотр.
  if (t?.start) {
    const s = toMinutesOfDay(t.start)
    const w = firstDateWindows(dayId).find((win) => {
      const ws = toMinutesOfDay(win.start.slice(11, 16))
      const we = toMinutesOfDay(win.end.slice(11, 16))
      return ws <= s && s < we
    })
    if (w) {
      const we = toMinutesOfDay(w.end.slice(11, 16))
      return buildDurations(s, we, props.step).map((x) => ({
        key: `${x.kind}:${x.minutes}`,
        label: x.kind === 'window' ? `Весь слот (${fmtDur(x.minutes)})` : fmtDur(x.minutes),
        minutes: x.minutes,
        kind: x.kind,
      }))
    }
  }
  const out = []
  for (let k = 1; k <= 8; k++) {
    out.push({ key: `step:${k * props.step}`, label: fmtDur(k * props.step) })
  }
  out.push({ key: 'window:', label: 'Весь слот' })
  return out
}

function onStart(dayId, timeKey) {
  const t = props.slot.weekdays[dayId].times.find((x) => x.key === timeKey)
  if (!t) return
  t.durKey = ''
  t.durationMin = null
  t.durationKind = ''
}

function onDuration(dayId, timeKey) {
  const t = props.slot.weekdays[dayId].times.find((x) => x.key === timeKey)
  if (!t) return
  const [kind, minutes] = String(t.durKey || '').split(':')
  t.durationKind = kind === 'window' ? 'window' : 'step'
  t.durationMin = kind === 'window' ? null : Number(minutes) || null
  if (!t.durationKind || (t.durationKind === 'step' && !t.durationMin)) {
    t.durKey = ''
  }
}
</script>

<style scoped>
/* Дни недели: чекбоксы в ряд, сокращённое название над каждым. */
.wd-row { display: flex; gap: 2px; }
.wd-check { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 11px; color: var(--color-gray-700); cursor: pointer; }
.wd-check input { width: auto; margin: 0; }
/* .day-card/.day-head/.day-title/.day-dates — из base.css (single source). */
</style>
