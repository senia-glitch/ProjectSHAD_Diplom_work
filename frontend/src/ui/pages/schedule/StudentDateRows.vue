<template>
  <div v-if="!slot.dates.length" class="pick-empty">Нажмите + возле «По дате», чтобы добавить даты</div>
  <div v-for="d in slot.dates" :key="d.key" class="nest">
    <div class="add-part">
      <span class="nest-title">Дата:</span>
      <input v-model="d.date" type="date" class="add-part-select" />
      <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать дату" @click="removeFormDate(d.key)">−</button>
    </div>
    <div class="add-part add-part--sub">
      <span class="nest-title">Время</span>
      <button type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить время" @click="addDateTime(d)">+</button>
    </div>
    <div v-for="t in d.times" :key="t.key" class="pick-block">
      <div class="add-part add-part--sub">
        <select v-model="t.win" class="add-part-select" @change="onWindow(d, t)">
          <option :value="''" disabled>Окно</option>
          <option v-for="(w, i) in dayWindows(d.date)" :key="i" :value="i">{{ fmtWin(w) }}</option>
        </select>
        <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать время" @click="removeDateTime(d, t.key)">−</button>
      </div>
      <div v-if="t.win !== ''" class="add-part add-part--sub">
        <select v-model="t.start" class="time-in" @change="onStart(d, t)">
          <option :value="''" disabled>Старт</option>
          <option v-for="s in startOptions(d, t)" :key="s" :value="s">{{ s }}</option>
        </select>
        <select v-model="t.durKey" class="time-in" @change="onDuration(d, t)">
          <option :value="''" disabled>Длительность</option>
          <option v-for="o in durationOptions(d, t)" :key="o.key" :value="o.key">{{ o.label }}</option>
        </select>
      </div>
    </div>
    <div v-if="d.date && !dayWindows(d.date).length" class="pick-empty">В этот день свободных окон нет</div>
  </div>
</template>

<script setup>
// Редактор режима «по дате» формы ученика: в каждой строке времени —
// структурный выбор окно → старт из сетки шага → длительность.
// Выборы сразу складываются в t.start/t.end, поэтому предпросмотр
// и создание работают общей механикой. Вложенные мутации слота.
import { buildStartGrid, buildDurations, toHHMM, toMinutesOfDay, fmtDur, fmtPreview } from '../../../logic/utils/index.js'

const props = defineProps({
  slot: { type: Object, required: true },
  windows: { type: Array, default: () => [] },
  step: { type: Number, default: 60 },
})

let rowSeq = 0

function addDateTime(dateObj) {
  dateObj.times.push({ key: ++rowSeq, win: '', start: '', end: '', durKey: '', durationKind: 'step' })
}

function removeDateTime(dateObj, timeKey) {
  dateObj.times = dateObj.times.filter((t) => t.key !== timeKey)
}

function removeFormDate(dateKey) {
  props.slot.dates = props.slot.dates.filter((d) => d.key !== dateKey)
}

function dayWindows(date) {
  if (!date) return []
  return props.windows.filter((w) => w.start.slice(0, 10) === date)
}

function fmtWin(w) {
  return fmtPreview(w.start.slice(0, 16), w.end.slice(0, 16))
}

function winOf(d, t) {
  const ws = dayWindows(d.date)
  const w = ws[Number(t.win)]
  return w || null
}

function onWindow(d, t) {
  t.start = ''
  t.end = ''
  t.durKey = ''
}

function startOptions(d, t) {
  const w = winOf(d, t)
  if (!w) return []
  const ws = toMinutesOfDay(w.start.slice(11, 16))
  const we = toMinutesOfDay(w.end.slice(11, 16))
  return buildStartGrid(ws, we, props.step).map(toHHMM)
}

function onStart(d, t) {
  t.end = ''
  t.durKey = ''
}

function durationOptions(d, t) {
  const w = winOf(d, t)
  if (!w || !t.start) return []
  const s = toMinutesOfDay(t.start)
  const we = toMinutesOfDay(w.end.slice(11, 16))
  return buildDurations(s, we, props.step).map((x) => ({
    key: `${x.kind}:${x.minutes}`,
    label: x.kind === 'window' ? `До конца окна (${fmtDur(x.minutes)})` : fmtDur(x.minutes),
    minutes: x.minutes,
    kind: x.kind,
  }))
}

function onDuration(d, t) {
  const w = winOf(d, t)
  if (!w || !t.start || !t.durKey) {
    t.end = ''
    return
  }
  const [kind, minutes] = String(t.durKey).split(':')
  const s = toMinutesOfDay(t.start)
  const we = toMinutesOfDay(w.end.slice(11, 16))
  const endMin = kind === 'window' ? we : s + Number(minutes)
  t.end = toHHMM(endMin)
  t.durationKind = kind
}
</script>

<style scoped>
.pick-block { display: flex; flex-direction: column; gap: 6px; }
</style>
