// Уроки: ветка репетитора и ветка ученика.
import { apiFetch, withQuery } from './client.js'

export function getTutorLessons({ dateFrom, dateTo, limit, offset } = {}) {
  return apiFetch(
    withQuery('/api/v1/tutor/me/lessons', { date_from: dateFrom, date_to: dateTo, limit, offset }),
  )
}

export function createTutorLesson({ startTime, endTime, isGroup }) {
  return apiFetch('/api/v1/tutor/lessons', {
    method: 'POST',
    body: { start_time: startTime, end_time: endTime, is_group: isGroup },
  })
}

export function patchTutorLesson(lessonId, patch) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}`, { method: 'PATCH', body: patch })
}

export function deleteTutorLesson(lessonId) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}`, { method: 'DELETE' })
}

export function getStudentLessons({ dateFrom, dateTo, limit, offset } = {}) {
  return apiFetch(
    withQuery('/api/v1/student/me/lessons', { date_from: dateFrom, date_to: dateTo, limit, offset }),
  )
}

export function getStudentAvailableSlots({ tutorUserId, dateFrom, dateTo }) {
  return apiFetch(
    withQuery(`/api/v1/student/tutors/${tutorUserId}/slots`, { date_from: dateFrom, date_to: dateTo }),
  )
}

export function getTutorLesson(lessonId) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}`)
}

export function getStudentLesson(lessonId) {
  return apiFetch(`/api/v1/student/lessons/${lessonId}`)
}

export function createStudentLesson({ tutorUserId, startTime, endTime }) {
  return apiFetch('/api/v1/student/lessons', {
    method: 'POST',
    body: { tutor_user_id: tutorUserId, start_time: startTime, end_time: endTime },
  })
}
