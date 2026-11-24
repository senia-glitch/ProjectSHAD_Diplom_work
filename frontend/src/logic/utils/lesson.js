// Поля страницы урока (/lessons/:id): чистые преобразования.
import { safeUrl } from './urls.js'
import { LESSON_STATUSES, STATUS_ACTORS, ABSENCE_LABELS } from '../constants/index.js'

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


export function lessonStatusLabel(status) {
  return LESSON_STATUSES.find((s) => s.value === status)?.label || status || ''
}

export function lessonStatusColor(status) {
  return LESSON_STATUSES.find((s) => s.value === status)?.color || 'var(--color-gray-600)'
}

// «26.11.2026 10:00» из наивной строки времени пользователя.
export function formatMoment(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(String(iso || ''))
  return m ? `${m[3]}.${m[2]}.${m[1]} ${m[4]}:${m[5]}` : ''
}

// Пометка статуса для человека: кто, когда и почему (история отмен, заявки, система).
export function describeStatusNote(note) {
  if (!note) return ''
  const who = STATUS_ACTORS[note.by] || ''
  const when = formatMoment(note.at)
  const reason = note.reason ? `. Причина: ${note.reason}` : ''
  if (note.scope === 'participant') {
    const action = note.by === 'student' ? 'Вы вышли из группового урока' : 'Репетитор убрал вас из группового урока'
    return `${action}${when ? ` ${when}` : ''}${reason}`
  }
  switch (note.status) {
    case 'PENDING':
      return 'Заявка ждёт подтверждения репетитора'
    case 'CANCELLED':
      return `Отменён${who ? ` ${who}` : ''}${when ? ` ${when}` : ''}${reason}`
    case 'REJECTED':
      return `Заявка отклонена${who ? ` ${who}` : ''}${when ? ` ${when}` : ''}${reason}`
    case 'SYSTEM_FINISHED':
      return `Завершён системой${when ? ` ${when}` : ''}${reason}. В оплатах не учитывается`
    default:
      return ''
  }
}

// Отпуск/болезнь репетитора, на которые пришёлся урок: заморожен, не отменён.
export function describeAbsence(absence) {
  if (!absence) return ''
  const label = ABSENCE_LABELS[absence.status] || 'отсутствует'
  return `Репетитор ${label} с ${formatMoment(absence.from)} по ${formatMoment(absence.to)} — урок заморожен`
}

// История статусов урока для показа (новые сверху).
export function statusHistoryLines(history) {
  return (history || [])
    .filter((e) => e && e.status)
    .map((e) => ({
      at: formatMoment(e.at),
      text: `${lessonStatusLabel(e.status)}${STATUS_ACTORS[e.by] ? ` — ${STATUS_ACTORS[e.by]}` : ''}${e.reason ? `: ${e.reason}` : ''}`,
    }))
    .reverse()
}
