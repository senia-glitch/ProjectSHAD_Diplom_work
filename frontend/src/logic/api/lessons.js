// Уроки: ветка репетитора и ветка ученика.
// Время на границе: в запросах — UTC (из пояса пользователя), в ответах — пояс пользователя.
import { apiFetch, withQuery } from './client.js'
import { lessonToUser, rangeToServer, toServerTime, toUserTime } from '../utils/tz.js'

const lessonsToUser = (data) => (data ? { ...data, lessons: (data.lessons || []).map((l) => lessonToUser(l)) } : data)

function timesToServer(body) {
  const out = { ...body }
  for (const key of ['start_time', 'end_time']) {
    if (out[key]) out[key] = toServerTime(out[key])
  }
  return out
}

export async function getTutorLessons({ dateFrom, dateTo, limit, offset } = {}) {
  const range = rangeToServer(dateFrom, dateTo)
  return lessonsToUser(await apiFetch(
    withQuery('/api/v1/tutor/me/lessons', { date_from: range.dateFrom, date_to: range.dateTo, limit, offset }),
  ))
}

export async function createTutorLesson({ startTime, endTime, isGroup }) {
  return lessonToUser(await apiFetch('/api/v1/tutor/lessons', {
    method: 'POST',
    body: timesToServer({ start_time: startTime, end_time: endTime, is_group: isGroup }),
  }))
}

export async function patchTutorLesson(lessonId, patch) {
  return lessonToUser(await apiFetch(`/api/v1/tutor/lessons/${lessonId}`, { method: 'PATCH', body: timesToServer(patch) }))
}

export function deleteTutorLesson(lessonId) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}`, { method: 'DELETE' })
}

// Заявка ученика: подтвердить или отклонить (с необязательной причиной).
export function confirmTutorLesson(lessonId, reason) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}/confirm`, { method: 'POST', body: { reason: reason || null } })
}

export function rejectTutorLesson(lessonId, reason) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}/reject`, { method: 'POST', body: { reason: reason || null } })
}

export async function getStudentLessons({ dateFrom, dateTo, limit, offset } = {}) {
  const range = rangeToServer(dateFrom, dateTo)
  return lessonsToUser(await apiFetch(
    withQuery('/api/v1/student/me/lessons', { date_from: range.dateFrom, date_to: range.dateTo, limit, offset }),
  ))
}

export async function getStudentAvailableSlots({ tutorUserId, dateFrom, dateTo }) {
  const range = rangeToServer(dateFrom, dateTo)
  const data = await apiFetch(
    withQuery(`/api/v1/student/tutors/${tutorUserId}/slots`, { date_from: range.dateFrom, date_to: range.dateTo }),
  )
  return data
    ? { ...data, slots: (data.slots || []).map((s) => ({ ...s, start: toUserTime(s.start), end: toUserTime(s.end) })) }
    : data
}

export async function getTutorLesson(lessonId) {
  return lessonToUser(await apiFetch(`/api/v1/tutor/lessons/${lessonId}`))
}

export async function getStudentLesson(lessonId) {
  return lessonToUser(await apiFetch(`/api/v1/student/lessons/${lessonId}`))
}

export async function createStudentLesson({ tutorUserId, startTime, endTime }) {
  return lessonToUser(await apiFetch('/api/v1/student/lessons', {
    method: 'POST',
    body: timesToServer({ tutor_user_id: tutorUserId, start_time: startTime, end_time: endTime }),
  }))
}

// Отмена урока учеником (или отзыв заявки) с необязательной причиной.
export function cancelStudentLesson(lessonId, reason) {
  return apiFetch(withQuery(`/api/v1/student/lessons/${lessonId}/leave`, { reason: reason || undefined }), {
    method: 'DELETE',
  })
}
