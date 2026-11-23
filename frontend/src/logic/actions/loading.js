// Порядковые номера загрузок: устаревший ответ (быстрая смена фильтров,
// навигация, выход) не должен затирать свежие данные в store.
const counters = new Map()

export function nextSeq(key) {
  const n = (counters.get(key) || 0) + 1
  counters.set(key, n)
  return n
}

export function isCurrentSeq(key, n) {
  return counters.get(key) === n
}

// Инвалидация всех in-flight загрузок (например, при logout).
export function invalidateAllLoads() {
  counters.clear()
}
