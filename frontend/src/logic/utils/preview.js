// Чистая генерация предпросмотра создаваемых уроков.
// Без состояния, без сети, без DOM. Мутаций входных данных нет.
import { WEEK_DAYS, PREVIEW_WEEKS_CAP } from '../constants/index.js'

export function validTime(t) {
  return Boolean(t.start && t.end && t.start < t.end)
}

export function parseLocalMs(s) {
  const ms = new Date(s).getTime()
  return Number.isNaN(ms) ? null : ms
}

export function periodWord(n) {
  if (n === 1) return 'неделю'
  if (n >= 2 && n <= 4) return 'недели'
  return 'недель'
}

export function buildPreview(slot, nowMs = Date.now()) {
  // Возвращает { items, skippedPast }. Прошедшее время в список не попадает.
  const now = nowMs
  const items = []
  let skippedPast = 0
  if (slot.mode === 'dates') {
    for (const d of slot.dates) {
      if (!d.date) continue
      for (const t of d.times) {
        if (!validTime(t)) continue
        const start = `${d.date}T${t.start}`
        const end = `${d.date}T${t.end}`
        const ms = parseLocalMs(start)
        if (ms === null) continue
        if (ms < now) {
          skippedPast++
          continue
        }
        items.push({ start, end })
      }
    }
  } else {
    // Weekly репетитора: у каждого включённого дня свои дата отсчёта,
    // кол-во и период. Дни без даты пропускаются.
    for (const d of WEEK_DAYS) {
      const cfg = (slot.weekdays || {})[d.id]
      if (!cfg || !cfg.on || !cfg.startDate) continue
      const k = Math.floor(Number(cfg.count)) || 0
      if (k < 1) continue
      const sMs = parseLocalMs(`${cfg.startDate}T00:00`)
      if (sMs === null) continue
      const monday = new Date(sMs)
      monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
      const i = WEEK_DAYS.findIndex((x) => x.id === d.id)
      const period = Math.max(1, Math.floor(Number(cfg.period)) || 1)
      let made = 0
      for (let w = 0; w < PREVIEW_WEEKS_CAP && made < k; w++) {
        if (w % period !== 0) continue
        const date = new Date(monday)
        date.setDate(date.getDate() + w * 7 + i)
        const ds = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
        for (const t of cfg.times || []) {
          if (!validTime(t)) continue
          const start = `${ds}T${t.start}`
          const end = `${ds}T${t.end}`
          const ms = parseLocalMs(start)
          if (ms === null) continue
          if (ms < now) {
            skippedPast++
            continue
          }
          items.push({ start, end })
          made++
          if (made >= k) break
        }
      }
    }
  }
  items.sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0))
  const sliced = items
  const seen = {}
  for (const it of sliced) {
    const base = `${it.start}|${it.end}`
    seen[base] = (seen[base] || 0) + 1
    it.key = `${base}#${seen[base]}`
  }
  return { items: sliced, skippedPast }
}

export function fpOf(slot) {
  return JSON.stringify({
    m: slot.mode,
    d: slot.dates.map((x) => [x.date, x.times.map((t) => [t.start, t.end])]),
    w: WEEK_DAYS.map((d) => {
      const c = slot.weekdays[d.id]
      return [c.on, c.period, c.startDate, c.count, c.times.map((t) => [t.start, t.end])]
    }),
  })
}

export function previewItems(slot, nowMs = Date.now()) {
  const drop = new Set(slot.dropped || [])
  return buildPreview(slot, nowMs).items.filter((it) => !drop.has(it.key))
}

export function skippedPastCount(slot, nowMs = Date.now()) {
  return buildPreview(slot, nowMs).skippedPast
}

export function hasSlotInput(slot) {
  if (slot.mode === 'dates') return slot.dates.length > 0
  return WEEK_DAYS.some((d) => slot.weekdays[d.id].on)
}

const WD_SHORT = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

export function fmtPreview(start, end) {
  const [d, t1] = start.split('T')
  const t2 = end.split('T')[1] || ''
  const [Y, M, D] = d.split('-')
  const wd = WD_SHORT[new Date(`${d}T00:00`).getDay()]
  return `${D}.${M} ${wd} ${t1.slice(0, 5)}–${t2.slice(0, 5)}`
}
