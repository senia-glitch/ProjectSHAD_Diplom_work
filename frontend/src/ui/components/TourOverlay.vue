<template>
  <div class="tour-overlay" @click.self="emit('close')">
    <div v-if="spot" class="tour-spot" :style="spot.boxStyle">
      <span class="tour-num">{{ stepIdx + 1 }}</span>
    </div>
    <div
      v-if="spot"
      class="tour-card"
      :class="`tour-card--${spot.place}`"
      :style="spot.cardStyle"
    >
      <div class="tour-top">
        <span class="tour-step">{{ stepIdx + 1 }} / {{ spots.length }}</span>
        <button type="button" class="tour-skip" @click="emit('close')">Пропустить</button>
      </div>
      <div class="tour-title">{{ spot.title }}</div>
      <div class="tour-text">{{ spot.text }}</div>
      <div v-if="spot.example?.length" class="tour-ex">
        <div class="tour-ex-cap">Пример</div>
        <div v-for="(line, i) in spot.example" :key="i" class="tour-ex-line">{{ line }}</div>
      </div>
      <div class="tour-nav">
        <span class="tour-dots">
          <span
            v-for="(_, i) in spots"
            :key="i"
            class="tour-dot"
            :class="{ 'tour-dot--active': i === stepIdx }"
          ></span>
        </span>
        <span class="tour-btns">
          <button
            v-if="stepIdx > 0"
            type="button"
            class="tour-back"
            @click="stepIdx--"
          >Назад</button>
          <button
            v-if="stepIdx < spots.length - 1"
            type="button"
            class="btn btn--pri btn--sm"
            @click="stepIdx++"
          >Далее</button>
          <button
            v-else
            type="button"
            class="btn btn--pri btn--sm"
            @click="emit('close')"
          >Понятно</button>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
// Общий движок обучающих туров (паттерн §11): светлый оверлей, одна тёмная
// подсказка за раз (что сделать + зачем), стрелка к элементу.
// Место карточки выбирается автоматически — где больше места.
// Шаги приходят пропсой: [{ id, sel, prefer, title, text, example? }].
// example — строки мини-примера содержимого блока (только на время тура).
// Пропущенные цели (нет элемента) молча пропускаются, нумерация пересчитывается.
// Длинные страницы автоскроллятся: цель шага всегда видна пользователю.
// Бизнеса не знает: только props и emits (UI-кит).
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  steps: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const GAP = 18
const CARD_W = 270
const CARD_H = 190
const EDGE = 12

const stepIdx = ref(0)
const spots = ref([])

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

// Оценка высоты карточки: пример растягивает её вниз.
function estH(st) {
  const ex = st.example?.length || 0
  return CARD_H + (ex ? 48 + ex * 19 : 0)
}

function pickPlace(r, prefer, h) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const need = { top: h + GAP, bottom: h + GAP, left: CARD_W + GAP, right: CARD_W + GAP }
  const space = { top: r.top, bottom: vh - r.bottom, left: r.left, right: vw - r.right }
  const order = [prefer, 'bottom', 'top', 'right', 'left'].filter((v, i, a) => a.indexOf(v) === i)
  return order.find((p) => space[p] >= need[p]) || prefer
}

function compute() {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const out = []
  props.steps.forEach((st) => {
    const el = document.querySelector(st.sel)
    if (!el) return
    const r = el.getBoundingClientRect()
    if (!r.width && !r.height) return
    const h = estH(st)
    const place = pickPlace(r, st.prefer, h)
    const boxStyle = {
      left: `${r.left - 5}px`,
      top: `${r.top - 5}px`,
      width: `${r.width + 10}px`,
      height: `${r.height + 10}px`,
    }
    let left
    let top
    if (place === 'top') {
      left = clamp(r.left + r.width / 2 - CARD_W / 2, EDGE, vw - CARD_W - EDGE)
      top = Math.max(EDGE, r.top - GAP - h)
    } else if (place === 'bottom') {
      left = clamp(r.left + r.width / 2 - CARD_W / 2, EDGE, vw - CARD_W - EDGE)
      top = clamp(r.bottom + GAP, EDGE, vh - EDGE)
    } else if (place === 'left') {
      left = Math.max(EDGE, r.left - GAP - CARD_W)
      top = clamp(r.top + r.height / 2 - h / 2, EDGE, vh - EDGE)
    } else {
      left = clamp(r.right + GAP, EDGE, vw - EDGE)
      top = clamp(r.top + r.height / 2 - h / 2, EDGE, vh - EDGE)
    }
    out.push({ ...st, place, rect: { top: r.top, bottom: r.bottom, height: r.height }, boxStyle, cardStyle: { left: `${left}px`, top: `${top}px`, width: `${CARD_W}px` } })
  })
  spots.value = out
  if (stepIdx.value > out.length - 1) stepIdx.value = Math.max(0, out.length - 1)
}

const spot = computed(() => spots.value[stepIdx.value] || null)

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}

// Длинные страницы: цель шага всегда в видимой зоне.
// Программный скролл работает и при залоченном body; карточка
// догоняет цель через пересчёт на событие scroll.
function ensureVisible() {
  const s = spots.value[stepIdx.value]
  if (!s?.rect) return
  const vh = window.innerHeight
  if (s.rect.top < 90 || s.rect.bottom > vh - 120) {
    window.scrollTo({
      top: Math.max(0, window.scrollY + s.rect.top + s.rect.height / 2 - vh / 2),
      behavior: 'smooth',
    })
    setTimeout(compute, 650)
  }
}

let scrollRaf = 0
function onScroll() {
  cancelAnimationFrame(scrollRaf)
  scrollRaf = requestAnimationFrame(compute)
}

watch(stepIdx, () => nextTick(ensureVisible))

let prevOverflow = ''

onMounted(() => {
  prevOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  compute()
  nextTick(ensureVisible)
  window.addEventListener('resize', compute)
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  document.body.style.overflow = prevOverflow
  cancelAnimationFrame(scrollRaf)
  window.removeEventListener('resize', compute)
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.tour-overlay {
  position: fixed; inset: 0; z-index: 150;
  background: var(--overlay);
  overflow-y: auto;
}
.tour-spot {
  position: fixed;
  border: 3px solid var(--color-accent);
  border-radius: 10px;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 22%, transparent), 0 0 0 1px var(--accent);
  pointer-events: none;
}
.tour-num {
  position: absolute; top: -15px; left: -15px;
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--color-accent); color: var(--on-accent);
  font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.tour-card {
  position: fixed;
  background: var(--surface); color: var(--text);
  border: 1px solid var(--line-strong); border-radius: 14px; padding: 14px 16px 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
}
.tour-card::after {
  content: ''; position: absolute; width: 16px; height: 16px;
  background: var(--surface); transform: rotate(45deg);
}
.tour-card--top::after { bottom: -8px; left: 50%; margin-left: -8px; }
.tour-card--bottom::after { top: -8px; left: 50%; margin-left: -8px; }
.tour-card--left::after { right: -8px; top: 50%; margin-top: -8px; }
.tour-card--right::after { left: -8px; top: 50%; margin-top: -8px; }
.tour-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.tour-step { font-size: 11px; font-weight: 600; letter-spacing: 0.5px; color: var(--muted); }
.tour-skip {
  background: none; border: none; cursor: pointer;
  font-size: 12px; color: var(--muted); text-decoration: underline;
  padding: 0;
}
.tour-skip:hover { color: var(--text); }
.tour-title { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
.tour-text { font-size: 13px; line-height: 1.5; color: var(--text); }
.tour-ex {
  margin-top: 10px; padding: 8px 10px;
  background: var(--surface-2); border-radius: 8px;
}
.tour-ex-cap {
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--muted); margin-bottom: 4px;
}
.tour-ex-line {
  font-size: 12px; line-height: 1.6; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tour-nav { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
.tour-dots { display: flex; gap: 5px; }
.tour-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--line-strong); }
.tour-dot--active { background: var(--accent); width: 18px; border-radius: 3px; }
.tour-btns { display: flex; gap: 8px; align-items: center; }
.tour-back {
  background: transparent; border: 1px solid var(--line-strong); border-radius: 8px;
  color: var(--text); font-size: 12px; font-weight: 500;
  padding: 5px 10px; cursor: pointer;
}
.tour-back:hover { border-color: var(--text); }
</style>
