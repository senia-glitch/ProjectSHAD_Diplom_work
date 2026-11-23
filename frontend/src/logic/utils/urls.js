// Санитизация URL перед рендером в :href.
// Серверные ссылки не должны исполняться как javascript:/data:.
// Разрешены только http(s). Небезопасный URL -> null (Vue уберёт href,
// ссылка станет некликабельным текстом).
export function safeUrl(url) {
  if (typeof url !== 'string') return null
  const s = url.trim()
  if (/^https?:\/\//i.test(s)) return s
  return null
}
