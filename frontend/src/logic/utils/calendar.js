// Календарь месяца: матрица дней, диапазон месяца, выборка уроков по дню.
// Чистые функции — страница только рисует и вызывает действия.
// Локальная ISO-дата: модуль не тянет статистику ради одной функции.

function isoOf(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function monthRangeISO(year, month) {
  // month — 1..12. Полуоткрытый интервал [первое, первое следующего).
  const first = new Date(year, month - 1, 1)
  const next = new Date(year, month, 1)
  return [isoOf(first), isoOf(next)]
}

export function shiftMonth(year, month, delta) {
  const d = new Date(year, month - 1 + delta, 1)
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

// Недели с понедельника; ячейки соседних месяцев — в матрице, но inMonth: false.
export function monthMatrix(year, month) {
  const first = new Date(year, month - 1, 1)
  const offset = (first.getDay() + 6) % 7
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells = Math.ceil((offset + daysInMonth) / 7) * 7
  const weeks = []
  for (let i = 0; i < cells; i++) {
    if (i % 7 === 0) weeks.push([])
    const d = new Date(year, month - 1, 1 - offset + i)
    weeks[weeks.length - 1].push({
      iso: isoOf(d),
      day: d.getDate(),
      inMonth: d.getMonth() === month - 1 && d.getFullYear() === year,
    })
  }
  return weeks
}

export function lessonDate(lesson) {
  return String(lesson?.start_time || '').slice(0, 10)
}

export function countByDay(lessons) {
  const counts = {}
  for (const l of lessons || []) {
    const key = lessonDate(l)
    if (!key) continue
    counts[key] = (counts[key] || 0) + 1
  }
  return counts
}

export function dayLessons(lessons, iso) {
  return (lessons || [])
    .filter((l) => lessonDate(l) === iso)
    .sort((a, b) => (String(a.start_time) < String(b.start_time) ? -1 : 1))
}
