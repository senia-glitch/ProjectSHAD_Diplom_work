// Чистые вычисления броней: пересечения интервалов.
// Принимают списки аргументами — состояния не читают.
import { toMin } from './datetime.js'

export function hasOverlap(bookings, day, start, end, excludeId) {
  const s = toMin(start)
  const e = toMin(end)
  return bookings.some((b) => {
    if (b.weekday !== day || (excludeId && b.id === excludeId)) return false
    return s < toMin(b.end_time) && e > toMin(b.start_time)
  })
}

export function blockGeometry(startTime, endTime, gridH) {
  const s = toMin(startTime)
  const e = toMin(endTime)
  const top = (s / 1440) * gridH
  const h = ((e - s) / 1440) * gridH
  return { top: `${top}px`, height: `${Math.max(h, 18)}px` }
}
