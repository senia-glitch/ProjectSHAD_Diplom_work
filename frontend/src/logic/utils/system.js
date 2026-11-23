// Форматирование системной телеметрии для страницы админа.

export function formatUptime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  const d = Math.floor(total / 86400)
  const h = Math.floor((total % 86400) / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (x) => String(x).padStart(2, '0')
  const clock = `${pad(h)}:${pad(m)}:${pad(s)}`
  return d > 0 ? `${d} д ${clock}` : clock
}

export function formatMs(ms) {
  const value = Number(ms) || 0
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} мс`
}

export function formatQueueLoad(channel) {
  const queue = Number(channel?.queue_size) || 0
  const pool = Number(channel?.pool_size) || 0
  if (!pool) return 'пул 0'
  const pct = Math.round((queue / pool) * 100)
  return `${queue} / ${pool} (${pct}%)`
}
