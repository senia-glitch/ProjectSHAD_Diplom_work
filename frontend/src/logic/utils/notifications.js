// Группировка уведомлений по дням: «Сегодня» / «Вчера» / дата.
// Чистые функции — живут в logic/utils, страница только рисует.

function toDate(value) {
  const d = new Date(String(value ?? '').replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

function dayStamp(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

function dayLabel(stamp, now) {
  const today = dayStamp(now)
  if (stamp === today) return 'Сегодня'
  if (stamp === today - 86400000) return 'Вчера'
  const d = new Date(stamp)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function formatNotifTime(value) {
  const d = toDate(value)
  if (!d) return String(value ?? '')
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function groupNotificationsByDay(items, now = new Date()) {
  const groups = []
  const byStamp = new Map()
  for (const item of items) {
    const d = toDate(item.created_at)
    const stamp = d ? dayStamp(d) : 0
    let group = byStamp.get(stamp)
    if (!group) {
      group = { key: String(stamp), label: dayLabel(stamp, now), items: [] }
      byStamp.set(stamp, group)
      groups.push(group)
    }
    group.items.push(item)
  }
  return groups
}
