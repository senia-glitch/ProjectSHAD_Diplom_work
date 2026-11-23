// Поля страницы урока (/lessons/:id): чистые преобразования.
import { safeUrl } from './urls.js'

// Ссылки урока показываем только валидные (§6.6 аутентификации: safeUrl).
export function lessonSafeLinks(links) {
  return (links || [])
    .map((l) => ({ alias: l?.alias || 'Ссылка', url: l?.url || '', safe: safeUrl(l?.url) }))
    .filter((l) => Boolean(l.safe))
}

// Имя репетитора из ростера ученика; без ростера — по её id.
export function tutorNameOf(lesson, tutors) {
  const found = (tutors || []).find((t) => t.tutor_id === lesson?.tutor_id)
  if (found?.full_name) return found.full_name
  return lesson?.tutor_id ? `Репетитор #${lesson.tutor_id}` : ''
}

export function lessonDateLabel(startTime) {
  if (!startTime) return ''
  const d = new Date(String(startTime).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(startTime).slice(0, 10)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function lessonTimeLabel(startTime, endTime) {
  const time = (v) => String(v || '').slice(11, 16)
  const s = time(startTime)
  const e = time(endTime)
  return s && e ? `${s}–${e}` : s || e
}
