// Чтение CSS-переменных дизайн-системы в runtime.
// Unovis ставит цвет SVG-атрибутом, а var() там ненадёжен,
// поэтому резолвим токены здесь. Hex в исходниках не храним.
const cache = new Map()

export function cssVar(name, fallback = '#3a7abd') {
  if (cache.has(name)) return cache.get(name)
  let value = fallback
  try {
    const raw = getComputedStyle(document.documentElement).getPropertyValue(name)
    if (raw && raw.trim()) value = raw.trim()
  } catch {
    value = fallback
  }
  cache.set(name, value)
  return value
}
