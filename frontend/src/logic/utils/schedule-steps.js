// Чистая логика шага записи ученика: сетка стартов и длительностей
// внутри свободного окна, проверка урока против окон, диапазон дат
// формы для запроса окон, превью записи ученика. Без состояния,
// без сети, без DOM. Время — минуты от полуночи; даты — 'YYYY-MM-DD'.
import { SLOTS_RANGE_MAX_DAYS, PREVIEW_WEEKS_CAP, WEEK_DAYS, TUTOR_COLORS } from '../constants/index.js'

export function toMinutesOfDay(hhmm) {
  const [h, m] = String(hhmm).split(':').map(Number)
  return h * 60 + m
}

export function toHHMM(min) {
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

export function isoToParts(iso) {
  const [date, time = ''] = String(iso).split('T')
  return { date, min: toMinutesOfDay(time.slice(0, 5)) }
}

function msOf(iso) {
  return new Date(String(iso)).getTime()
}

// Сетка стартов от начала окна с шагом stepMin.
// Старт существует, если от него помещается хотя бы один шаг;
// если окно короче шага — единственный старт window_start.
export function buildStartGrid(winStartMin, winEndMin, stepMin) {
  const out = []
  if (!(winEndMin > winStartMin) || !(stepMin > 0)) return out
  if (winEndMin - winStartMin < stepMin) return [winStartMin]
  for (let s = winStartMin; s + stepMin <= winEndMin; s += stepMin) {
    out.push(s)
  }
  return out
}

// Длительности от выбранного старта: кратные шагу (а) плюс
// «до конца окна» (б), если остаток не кратен шагу (иначе дублировать не нужно).
// Возвращает [{ minutes, kind: 'step' | 'window' }].
export function buildDurations(startMin, winEndMin, stepMin) {
  const out = []
  if (!(winEndMin > startMin) || !(stepMin > 0)) return out
  for (let k = 1; startMin + k * stepMin <= winEndMin; k++) {
    out.push({ minutes: k * stepMin, kind: 'step' })
  }
  const rest = winEndMin - startMin
  if (rest % stepMin !== 0) {
    out.push({ minutes: rest, kind: 'window' })
  }
  return out
}

// Окно, целиком содержащее [startIso, endIso]. Окна и урок —
// локальные ISO без таймзоны, сравнение через ms корректно.
export function findWindow(windows, startIso, endIso) {
  const s = msOf(startIso)
  const e = msOf(endIso)
  if (Number.isNaN(s) || Number.isNaN(e) || !(e > s)) return null
  for (const w of windows || []) {
    const ws = msOf(w.start)
    const we = msOf(w.end)
    if (!Number.isNaN(ws) && !Number.isNaN(we) && ws <= s && e <= we) {
      return w
    }
  }
  return null
}

// Проверка урока из предпросмотра: внутри окна, старт на сетке шага
// от начала окна, длительность кратна шагу либо равна окну целиком.
export function validateItemAgainstWindows(item, windows, stepMin) {
  const w = findWindow(windows, item.start, item.end)
  if (!w) return { ok: false, reason: 'outside' }
  if (!(stepMin > 0)) return { ok: false, reason: 'bad-step' }
  const ws = isoToParts(w.start).min
  const s = isoToParts(item.start).min
  const e = isoToParts(item.end).min
  if ((s - ws) % stepMin !== 0) return { ok: false, reason: 'off-grid' }
  const dur = e - s
  const we = isoToParts(w.end).min
  if (dur % stepMin !== 0 && e !== we) return { ok: false, reason: 'bad-duration' }
  return { ok: true, reason: '' }
}

function addDaysStr(ds, n) {
  const d = new Date(`${ds}T00:00`)
  d.setDate(d.getDate() + n)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function diffDays(a, b) {
  return Math.round((new Date(`${b}T00:00`) - new Date(`${a}T00:00`)) / 86400000)
}

// Даты правила «по дням недели»: от недели startDate вперёд,
// не больше cap штук. Чистый генератор для структурированных строк.
export function generateWeeklyDates(rule, cap = 62) {
  if (!rule?.startDate) return []
  const sMs = new Date(`${rule.startDate}T00:00`).getTime()
  if (Number.isNaN(sMs)) return []
  const monday = new Date(sMs)
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
  const onDays = WEEK_DAYS.map((d, i) => ({ i, cfg: (rule.weekdays || {})[d.id] })).filter(
    (x) => x.cfg && x.cfg.on,
  )
  if (!onDays.length) return []
  const out = []
  for (let w = 0; w < 500 && out.length < cap; w++) {
    for (const { i, cfg } of onDays) {
      if (w % Math.max(1, Math.floor(Number(cfg.period)) || 1) !== 0) continue
      const date = new Date(monday)
      date.setDate(date.getDate() + w * 7 + i)
      out.push(fmtDay(date))
      if (out.length >= cap) break
    }
  }
  return out
}

// Диапазон дат формы для запроса окон: dates — мин/макс даты,
// weekly — от startDate на длину периода (по count и периодам дней),
// но не шире SLOTS_RANGE_MAX_DAYS. Нет ввода — null.
export function slotRangeFromSlot(slot) {
  let from = ''
  let to = ''
  if (slot.mode === 'dates') {
    const ds = (slot.dates || []).map((d) => d.date).filter(Boolean).sort()
    if (!ds.length) return null
    from = ds[0]
    to = ds[ds.length - 1]
  } else {
    // Диапазон — объединение по дням: у каждого своя дата отсчёта,
    // своё кол-во и свой период.
    let found = false
    for (const d of WEEK_DAYS) {
      const cfg = (slot.weekdays || {})[d.id]
      if (!cfg || !cfg.on || !cfg.startDate) continue
      const k = Math.max(0, Math.floor(Number(cfg.count)) || 0)
      if (k < 1) continue
      const period = Math.max(1, Math.floor(Number(cfg.period)) || 1)
      const end = addDaysStr(cfg.startDate, k * period * 7 + 7)
      if (!found || cfg.startDate < from) from = cfg.startDate
      if (!found || end > to) to = end
      found = true
    }
    if (!found) return null
  }
  if (diffDays(from, to) > SLOTS_RANGE_MAX_DAYS) {
    to = addDaysStr(from, SLOTS_RANGE_MAX_DAYS)
  }
  return { dateFrom: from, dateTo: to }
}

export function fmtDur(min) {
  if (min < 60) return `${min} мин`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h} ч ${m} мин` : `${h} ч`
}

// Видимость ссылок урока ученику: выключено — всегда видны;
// включено — с (start − lead) и позже. Без конфигурации — видны.
export function lessonLinksVisible(cfg, startIso, nowMs = Date.now()) {
  if (!cfg || !cfg.link_visibility_enabled) return true
  const start = new Date(startIso).getTime()
  if (Number.isNaN(start)) return true
  const lead = Math.max(0, Number(cfg.link_lead_time_minutes) || 0)
  return nowMs >= start - lead * 60000
}

// Сколько целых минут осталось до появления ссылок (0 — уже видны).
export function lessonLinksRemainingMin(cfg, startIso, nowMs = Date.now()) {
  if (lessonLinksVisible(cfg, startIso, nowMs)) return 0
  const start = new Date(startIso).getTime()
  const lead = Math.max(0, Number(cfg?.link_lead_time_minutes) || 0)
  return Math.max(0, Math.ceil((start - lead * 60000 - nowMs) / 60000))
}

// Итоговый цвет репетитора: ручной выбор (customMap) либо
// детерминированный по порядку в списке связанных. Пустого
// результата нет никогда — сетка всегда цветная, а не зелёная.
export function resolveTutorColor(tutorUserId, tutors, customMap) {
  const custom = customMap?.[tutorUserId]
  if (custom && TUTOR_COLORS.some((c) => c.id === custom)) return custom
  const idx = (tutors || []).findIndex((t) => t.tutor_user_id === tutorUserId)
  return TUTOR_COLORS[(idx < 0 ? 0 : idx) % TUTOR_COLORS.length].id
}

function fmtDay(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Превью записи ученика: dates — готовые строки (окно→старт→длительность),
// weekly — развёртка правила с подбором окна на каждую дату.
// Каждый элемент: { start, end, key, ok, reason }.
// reason: '' | 'outside' | 'off-grid' | 'bad-duration'.
// Прошедшее время не попадает (skippedPast), ручные удаления — через slot.dropped.
export function buildStudentPreview(slot, windows, stepMin, nowMs = Date.now()) {
  const step = stepMin > 0 ? stepMin : 60
  const items = []
  let skippedPast = 0
  const push = (start, end, ok, reason) => {
    const ms = new Date(start).getTime()
    if (Number.isNaN(ms)) return
    if (ms < nowMs) {
      skippedPast++
      return
    }
    items.push({ start, end, ok, reason })
  }
  const wins = (windows || [])
    .map((w) => ({ ...w, sMs: new Date(w.start).getTime(), eMs: new Date(w.end).getTime() }))
    .filter((w) => !Number.isNaN(w.sMs) && !Number.isNaN(w.eMs) && w.eMs > w.sMs)
  const winForStart = (sMs) => wins.find((w) => w.sMs <= sMs && sMs < w.eMs) || null

  if (slot.mode === 'dates') {
    for (const d of slot.dates || []) {
      if (!d.date) continue
      for (const t of d.times || []) {
        if (!t.start || !t.end || !(t.start < t.end)) continue
        const start = `${d.date}T${t.start}`
        const end = `${d.date}T${t.end}`
        const v = validateItemAgainstWindows({ start, end }, windows, step)
        push(start, end, v.ok, v.reason)
      }
    }
  } else {
    // Weekly: у каждого отмеченного дня свои дата отсчёта, кол-во
    // и строки времени. Отсчёт дат — от недели startDate дня.
    // Невалидных показываем не больше 10 всего, чтобы пустые
    // недели не раздували список.
    let invalidCount = 0
    let done = false
    for (const d of WEEK_DAYS) {
      if (done) break
      const cfg = (slot.weekdays || {})[d.id]
      if (!cfg || !cfg.on || !cfg.startDate) continue
      const k = Math.max(0, Math.floor(Number(cfg.count)) || 0)
      if (k < 1) continue
      const sMs = new Date(`${cfg.startDate}T00:00`).getTime()
      if (Number.isNaN(sMs)) continue
      const monday = new Date(sMs)
      monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
      const dayIdx = WEEK_DAYS.findIndex((x) => x.id === d.id)
      const period = Math.max(1, Math.floor(Number(cfg.period)) || 1)
      let validCount = 0
      for (let w = 0; w < PREVIEW_WEEKS_CAP && validCount < k && !done; w++) {
        if (w % period !== 0) continue
        const date = new Date(monday)
        date.setDate(date.getDate() + w * 7 + dayIdx)
        const ds = fmtDay(date)
        if (ds < cfg.startDate) continue
        for (const t of cfg.times || []) {
          if (!t.start || !t.durationKind) continue
          const start = `${ds}T${t.start}`
          const sMs2 = new Date(start).getTime()
          if (Number.isNaN(sMs2)) continue
          if (sMs2 < nowMs) {
            skippedPast++
            continue
          }
          const win = winForStart(sMs2)
          if (!win) {
            push(start, start, false, 'outside')
            invalidCount++
          } else if ((isoToParts(start).min - isoToParts(win.start).min) % step !== 0) {
            push(start, start, false, 'off-grid')
            invalidCount++
          } else if (t.durationKind === 'window') {
            push(start, win.end.slice(0, 16), true, '')
            validCount++
          } else {
            const dur = Math.max(0, Math.floor(Number(t.durationMin)) || 0)
            const eMs = sMs2 + dur * 60000
            if (dur <= 0 || eMs > win.eMs) {
              push(start, start, false, 'bad-duration')
              invalidCount++
            } else {
              const e = new Date(eMs)
              const end = `${ds}T${String(e.getHours()).padStart(2, '0')}:${String(e.getMinutes()).padStart(2, '0')}`
              push(start, end, true, '')
              validCount++
            }
          }
          if (validCount >= k || invalidCount >= 10) {
            done = true
            break
          }
        }
      }
    }
  }
  items.sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0))
  const seen = {}
  const drop = new Set(slot.dropped || [])
  const out = []
  for (const it of items) {
    const base = `${it.start}|${it.end}`
    seen[base] = (seen[base] || 0) + 1
    const key = `${base}#${seen[base]}`
    if (!drop.has(key)) out.push({ ...it, key })
  }
  return { items: out, skippedPast }
}
