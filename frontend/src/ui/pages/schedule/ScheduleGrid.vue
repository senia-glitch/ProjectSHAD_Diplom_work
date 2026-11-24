<template>
  <div class="grid-wrap">
    <div class="calendar-nav">
      <button type="button" class="btn-nav" aria-label="Предыдущая неделя" title="Предыдущая неделя" @click="emit('nav-prev')"><UiIcon name="arrowLeft" /></button>
      <span class="week-range">{{ weekRange }}</span>
      <button type="button" class="btn-nav" aria-label="Следующая неделя" title="Следующая неделя" @click="emit('nav-next')"><UiIcon name="arrowRight" /></button>
      <button class="btn btn--gry" @click="emit('nav-today')">Сегодня</button>
      <label v-if="dimBookings.length" class="dim-toggle" title="Показать фоновые брони">
        <input type="checkbox" v-model="showDim" /> Брони
      </label>
    </div>
    <p class="grid-hint">Прокрутите сетку, чтобы увидеть остальные дни и часы.</p>
    <div class="grid-scroll" role="region" tabindex="0" aria-label="Сетка недели. Прокрутите, чтобы увидеть остальные дни и часы.">
    <div class="grid-container">
      <div class="grid-header">
        <div class="corner"></div>
        <div v-for="d in weekDays" :key="d.date" class="day-head" :class="{ 'day-head--today': d.isToday }">
          <span class="day-name">{{ d.name }}</span>
          <span class="day-num">{{ d.num }}</span>
        </div>
      </div>
      <div class="grid-body" :style="{ height: dynamicGridH + 'px' }" @click="emit('grid-clear')">
        <div class="time-col">
          <div v-for="h in visibleHours" :key="h" class="time-slot">
            <span class="time-lbl">{{ String(h).padStart(2, '0') }}:00</span>
          </div>
        </div>
        <div v-for="d in weekDays" :key="d.date" class="day-col" :class="{ 'day-col--today': d.isToday }">
          <div v-for="h in visibleHours" :key="h" class="hour-cell"></div>
          <div
            v-for="l in lessonsOfDay(d.date)"
            :key="l.lesson_id"
            class="block block--lesson"
            role="button" tabindex="0"
            :aria-label="`${fmtTime(l.start_time)}–${fmtTime(l.end_time)}, ${statusLabel(l)}`"
            :aria-pressed="selectedIds.has(l.lesson_id)"
            @keydown.enter.stop.prevent="emit('lesson-select', l, $event)"
            @keydown.space.stop.prevent="emit('lesson-select', l, $event)"
            :class="{
              'block--sel': selectedIds.has(l.lesson_id),
              'block--pending': l.status === 'PENDING',
              'block--inactive': l.status === 'CANCELLED' || l.status === 'REJECTED',
              'block--frozen': Boolean(l.absence) && l.status !== 'CANCELLED' && l.status !== 'REJECTED',
            }"
            :style="lessonStyle(l)"
            @click.stop="emit('lesson-select', l, $event)"
          ><span v-if="statusColor(l)" class="block-dot" :style="{ background: statusColor(l) }" :title="statusLabel(l)"></span><span class="block-txt">{{ fmtTime(l.start_time) }}–{{ fmtTime(l.end_time) }}</span><span v-if="l.absence && l.status !== 'CANCELLED' && l.status !== 'REJECTED'" class="block-flag" title="Урок пришёлся на отпуск/болезнь репетитора">❄</span></div>
          <template v-if="showDim">
            <div
              v-for="g in dimOfDay(d.date)"
              :key="g.lesson_id"
              class="block block--dim"
              :class="`block--dim-${String(g.rule || 'everyone').toLowerCase()}`"
              :style="lessonStyle(g)"
              :title="`Бронь · ${dimRuleLabel(g.rule)} · ${fmtTime(g.start_time)}–${fmtTime(g.end_time)}`"
            ></div>
          </template>
        <div
          v-for="w in freeOfDay(d.date)"
          :key="`free-${w.tutorUserId}-${w.start}-${w.end}`"
          class="block block--free"
          :class="[w.colorId ? `free--${w.colorId}` : '', w.outlined ? 'block--outlined' : '']"
          :style="lessonStyle({ start_time: w.start, end_time: w.end })"
          :title="`Свободно · ${w.tutorName || ''} ${fmtTime(w.start)}–${fmtTime(w.end)}`.trim()"
        ><span class="block-txt">{{ fmtTime(w.start) }}–{{ fmtTime(w.end) }}</span></div>
        <div
          v-for="b in previewOfDay(d.date)"
          :key="b.lesson_id"
          class="block block--preview"
          :style="lessonStyle(b)"
          title="Предпросмотр — ещё не создан"
        ><span class="block-txt">{{ fmtTime(b.start_time) }}–{{ fmtTime(b.end_time) }}</span></div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
// Сетка недели: только отображение. Данные — пропсами, действия — эмитами.
// Чистая математика позиций — из logic/utils, цвета правил — из constants.
import { ref, computed } from 'vue'
import { UiIcon } from '../../components/index.js'
import { toDateStr, toMinutes, fmtTime } from '../../../logic/utils/index.js'
import { WEEKDAY_ORDER, RULE_LABELS, MONTHS_SHORT, LESSON_STATUSES } from '../../../logic/constants/index.js'

const props = defineProps({
  lessons: { type: Array, default: () => [] },
  dimBookings: { type: Array, default: () => [] },
  previewBlocks: { type: Array, default: () => [] },
  freeWindows: { type: Array, default: () => [] },
  tutorColors: { type: Object, default: () => ({}) },
  outlinedWeekdays: { type: Array, default: () => [] },
  weekDays: { type: Array, default: () => [] },
  visibleHours: { type: Array, default: () => [] },
  dynamicGridH: { type: Number, default: 600 },
  selectedIds: { type: Object, default: () => new Set() },
})

const weekRange = computed(() => {
  if (!props.weekDays.length) return ''
  const s = new Date(props.weekDays[0].date)
  const e = new Date(props.weekDays[6].date)
  return `${s.getDate()} ${MONTHS_SHORT[s.getMonth()]} — ${e.getDate()} ${MONTHS_SHORT[e.getMonth()]}`
})
const emit = defineEmits(['lesson-select', 'grid-clear', 'nav-prev', 'nav-next', 'nav-today'])

// Фон броней — чисто визуальный тумблер (по умолчанию выключен,
// никуда не сохраняется, на бэкенд не влияет).
const showDim = ref(false)

function lessonsOfDay(ds) {
  return props.lessons.filter((l) => toDateStr(l.start_time) === ds)
}

function previewOfDay(ds) {
  return props.previewBlocks.filter((b) => toDateStr(b.start_time) === ds)
}

// Свободные окна репетитора для ученика (конкретные даты, уже
// с вычтенными уроками). Цвет — из карты репетитор→палитра.
// Пусто для репетитора — слой не рисуется.
function freeOfDay(ds) {
  const wd = WEEKDAY_ORDER[(new Date(`${ds}T00:00`).getDay() + 6) % 7]
  const outlined = props.outlinedWeekdays.includes(wd)
  return props.freeWindows
    .filter((w) => toDateStr(w.start) === ds)
    .map((w) => ({ ...w, colorId: props.tutorColors[w.tutorUserId] || null, outlined }))
}

function dimOfDay(ds) {
  const wd = WEEKDAY_ORDER[(new Date(`${ds}T00:00`).getDay() + 6) % 7]
  return props.dimBookings
    .filter((b) => b.weekday === wd)
    .map((b) => ({
      lesson_id: `dim-${b.booking_id}`,
      start_time: `${ds}T${String(b.start_time).slice(0, 5)}`,
      end_time: `${ds}T${String(b.end_time).slice(0, 5)}`,
      rule: b.access_rule,
    }))
}

function dimRuleLabel(rule) {
  return RULE_LABELS[rule] || rule
}

// Значок статуса урока: единая форма (точка) для любого статуса,
// цвет — по статусу, название — в подсказке. Без статуса — нет значка.
function statusEntry(lesson) {
  return LESSON_STATUSES.find((s) => s.value === lesson.status) || null
}

function statusColor(lesson) {
  return statusEntry(lesson)?.color || ''
}

function statusLabel(lesson) {
  return statusEntry(lesson)?.label || ''
}

function lessonStyle(l) {
  const s = toMinutes(l.start_time)
  const e = toMinutes(l.end_time)
  const totalMinutes = props.visibleHours.length * 60
  if (totalMinutes <= 0) return { top: '0px', height: '18px' }
  const offset = props.visibleHours[0] * 60
  const top = ((s - offset) / totalMinutes) * props.dynamicGridH
  const h = ((e - s) / totalMinutes) * props.dynamicGridH
  return { top: `${top}px`, height: `${Math.max(h, 18)}px` }
}</script>

<style scoped>
.calendar-nav { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.week-range { font-size: 16px; font-weight: 500; min-width: 0; flex: 1; text-align: center; }
.btn-nav {
  width: 32px; height: 32px; border: 1px solid var(--color-gray-300); border-radius: 6px;
  background: var(--color-white); font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.btn-nav:hover { background: var(--color-gray-100); }
.dim-toggle {
  display: flex; align-items: center; gap: 6px; margin-left: auto;
  font-size: 13px; font-weight: 500; color: var(--color-gray-700); cursor: pointer;
  white-space: nowrap;
}
.dim-toggle input { width: auto; margin: 0; }

/* === GRID === */
.grid-wrap { flex: 1; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.grid-container {
  background: var(--color-white); border-radius: 12px; border: 1px solid var(--color-gray-200);
  display: flex; flex-direction: column; overflow: hidden; flex: 1;
}
.grid-header {
  display: grid; grid-template-columns: 44px repeat(7, 1fr);
  background: var(--color-gray-50); border-bottom: 2px solid var(--color-gray-200); flex-shrink: 0;
}
.corner { border-right: 1px solid var(--color-gray-200); }
.day-head {
  text-align: center; padding: 8px 2px; font-size: 13px; font-weight: 600;
  color: var(--color-gray-700); border-right: 1px solid var(--color-gray-100); display: flex; flex-direction: column; gap: 2px;
}
.day-head--today { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.day-name { font-size: 11px; color: var(--color-gray-600); font-weight: 500; }
.day-head:last-child { border-right: none; }

.grid-body {
  display: grid; grid-template-columns: 44px repeat(7, 1fr);
  overflow: hidden;
}
.time-col { border-right: 1px solid var(--color-gray-200); }
.time-slot {
  height: 25px; display: flex; align-items: flex-start; justify-content: flex-end;
  padding: 0 4px; border-bottom: 1px solid var(--color-gray-100);
}
.time-lbl {
  font-size: 10px; color: var(--color-gray-500); font-variant-numeric: tabular-nums;
  position: relative; top: -6px; background: var(--color-white); padding: 0 2px;
}
/* Подпись самого верхнего часа не уезжает вверх под шапку таблицы. */
.time-col .time-slot:first-child .time-lbl { top: 0; }
.day-col { position: relative; border-right: 1px solid var(--color-gray-100); }
.day-col--today { background: color-mix(in srgb, var(--accent) 3%, transparent); }
.day-col:last-child { border-right: none; }
.hour-cell { height: 25px; border-bottom: 1px solid var(--color-gray-100); }

.block {
  position: absolute; left: 2px; right: 2px; border-radius: 5px;
  cursor: pointer; z-index: 10; display: flex; align-items: center;
  justify-content: center; transition: box-shadow 120ms;
  border: 1px solid transparent; overflow: hidden;
}
.block:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.18); z-index: 20; }
.block--sel { box-shadow: 0 0 0 2px var(--color-accent); z-index: 25; }
.block-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-right: 3px; }
.block-txt {
  font-size: 11px; font-weight: 600; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; padding: 0 3px; line-height: 1.2;
}
.block--lesson { background: var(--lesson-block-bg); color: var(--lesson-block-text); border-color: var(--lesson-block-border); }
/* Заявка ждёт подтверждения, отменённые/отклонённые приглушены, замороженные (отпуск) помечены. */
.block--pending { border-style: dashed; border-color: var(--rule-only-border, #d4a72c); }
.block--inactive { opacity: .5; }
.block--inactive .block-txt { text-decoration: line-through; }
.block--frozen { border-style: dotted; border-color: var(--rule-except-border, #c77d3a); }
.block-flag { margin-left: 4px; font-size: 10px; }
/* Превью создаваемых уроков: серая штриховка, поверх реальных.
   Некликабельные — клики проходят сквозь на сетку. */
.block--preview {
  background: repeating-linear-gradient(45deg, rgba(134,142,150,0.28) 0 4px, rgba(134,142,150,0.10) 4px 8px);
  color: var(--color-gray-700); border: 1px dashed var(--color-gray-600);
  pointer-events: none; z-index: 15;
}
/* Фоновые брони: цвета правил как на странице броней, но тускло.
   Некликабельные, лежат под уроками (z 5 < 10) и превью (15). */
.block--dim { pointer-events: none; z-index: 5; opacity: 0.45; border-style: dotted; }
.block--dim-everyone { background: var(--rule-everyone-bg); color: var(--rule-everyone-text); border-color: var(--rule-everyone-border); }
.block--dim-only { background: var(--rule-only-bg); color: var(--rule-only-text); border-color: var(--rule-only-border); }
.block--dim-all_except { background: var(--rule-all-except-bg); color: var(--rule-all-except-text); border-color: var(--rule-all-except-border); }
.block--dim-nobody { background: var(--rule-nobody-bg); color: var(--rule-nobody-text); border-color: var(--rule-nobody-border); }
/* Свободные окна репетитора для ученика: цвета «открыто всем»,
   некликабельные, лежат под уроками (z 5 < 10) и превью (15). */
.block--free {
  background: var(--rule-everyone-bg); color: var(--rule-everyone-text);
  border: 1px dotted var(--rule-everyone-border);
  pointer-events: none; z-index: 5;
}
/* Выбранные в weekly-формах дни: та же подсветка, но жирный пунктир. */
.block--free.block--outlined { border-width: 3px; }
/* Цвета репетиторов: только оттенок (var(--tutor-c*)),
   заливка/рамка/прозрачность едины для всех. */
.free--c1 { background: color-mix(in srgb, var(--tutor-c1) 16%, var(--surface)); color: var(--tutor-c1); border: 1px dotted var(--tutor-c1); }
.free--c2 { background: color-mix(in srgb, var(--tutor-c2) 16%, var(--surface)); color: var(--tutor-c2); border: 1px dotted var(--tutor-c2); }
.free--c3 { background: color-mix(in srgb, var(--tutor-c3) 16%, var(--surface)); color: var(--tutor-c3); border: 1px dotted var(--tutor-c3); }
.free--c4 { background: color-mix(in srgb, var(--tutor-c4) 16%, var(--surface)); color: var(--tutor-c4); border: 1px dotted var(--tutor-c4); }
.free--c5 { background: color-mix(in srgb, var(--tutor-c5) 16%, var(--surface)); color: var(--tutor-c5); border: 1px dotted var(--tutor-c5); }
.free--c6 { background: color-mix(in srgb, var(--tutor-c6) 16%, var(--surface)); color: var(--tutor-c6); border: 1px dotted var(--tutor-c6); }
.free--c7 { background: color-mix(in srgb, var(--tutor-c7) 16%, var(--surface)); color: var(--tutor-c7); border: 1px dotted var(--tutor-c7); }
.free--c8 { background: color-mix(in srgb, var(--tutor-c8) 16%, var(--surface)); color: var(--tutor-c8); border: 1px dotted var(--tutor-c8); }
.free--c9 { background: color-mix(in srgb, var(--tutor-c9) 16%, var(--surface)); color: var(--tutor-c9); border: 1px dotted var(--tutor-c9); }
.free--c10 { background: color-mix(in srgb, var(--tutor-c10) 16%, var(--surface)); color: var(--tutor-c10); border: 1px dotted var(--tutor-c10); }
.free--c11 { background: color-mix(in srgb, var(--tutor-c11) 16%, var(--surface)); color: var(--tutor-c11); border: 1px dotted var(--tutor-c11); }
.free--c12 { background: color-mix(in srgb, var(--tutor-c12) 16%, var(--surface)); color: var(--tutor-c12); border: 1px dotted var(--tutor-c12); }
.free--c13 { background: color-mix(in srgb, var(--tutor-c13) 16%, var(--surface)); color: var(--tutor-c13); border: 1px dotted var(--tutor-c13); }
.free--c14 { background: color-mix(in srgb, var(--tutor-c14) 16%, var(--surface)); color: var(--tutor-c14); border: 1px dotted var(--tutor-c14); }
.free--c15 { background: color-mix(in srgb, var(--tutor-c15) 16%, var(--surface)); color: var(--tutor-c15); border: 1px dotted var(--tutor-c15); }
.free--c16 { background: color-mix(in srgb, var(--tutor-c16) 16%, var(--surface)); color: var(--tutor-c16); border: 1px dotted var(--tutor-c16); }
.free--c17 { background: color-mix(in srgb, var(--tutor-c17) 16%, var(--surface)); color: var(--tutor-c17); border: 1px dotted var(--tutor-c17); }
.free--c18 { background: color-mix(in srgb, var(--tutor-c18) 16%, var(--surface)); color: var(--tutor-c18); border: 1px dotted var(--tutor-c18); }

.grid-scroll { overflow: auto; max-height: 680px; border: 1px solid var(--line); border-radius: var(--radius-lg); scrollbar-width: thin; scrollbar-color: var(--line-strong) var(--surface); }
.grid-container { min-width: 560px; border: 0; border-radius: 0; }
.grid-header { position: sticky; top: 0; z-index: 30; border-bottom-width: 1px; }
.grid-header, .grid-body { grid-template-columns: 48px repeat(7, minmax(0, 1fr)); }
.time-lbl { font-size: 10px; color: var(--muted); }
.day-head { padding-block: 12px; }
.day-head--today { color: var(--accent); background: var(--accent-soft); }
.day-num { font-size: 17px; }
@media (max-width: 600px) {
  .grid-scroll { max-height: 520px; }
  .calendar-nav { gap: 8px; }
  .week-range { font-size: 13px; }
}

.grid-hint { display: none; font-size: 11px; color: var(--muted); }
@media (max-width: 600px) { .grid-hint { display: block; } }
</style>
