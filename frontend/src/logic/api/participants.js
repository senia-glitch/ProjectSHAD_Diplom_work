// Участники урока.
import { apiFetch } from './client.js'

export function getLessonParticipants(lessonId) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}/participants`)
}

export function addLessonParticipant(lessonId, { studentUserId }) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}/participants`, {
    method: 'POST',
    body: { student_user_id: studentUserId },
  })
}

export function removeLessonParticipant(lessonId, studentUserId) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}/participants/${studentUserId}`, {
    method: 'DELETE',
  })
}

export function setLessonParticipantPaid(lessonId, studentUserId, paid) {
  return apiFetch(`/api/v1/tutor/lessons/${lessonId}/participants/${studentUserId}/payment`, {
    method: 'PATCH',
    body: { paid: Boolean(paid) },
  })
}
