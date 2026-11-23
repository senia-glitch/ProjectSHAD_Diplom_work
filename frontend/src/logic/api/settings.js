// Профиль и настройки репетитора.
import { apiFetch } from './client.js'

export function getTutorProfile() {
  return apiFetch('/api/v1/tutor/me')
}

export function patchTutorSettings(patch) {
  return apiFetch('/api/v1/tutor/me/settings', { method: 'PATCH', body: patch })
}

// Профиль и настройки ученика.
export function getStudentProfile() {
  return apiFetch('/api/v1/student/me')
}

export function patchStudentSettings(patch) {
  return apiFetch('/api/v1/student/me/settings', { method: 'PATCH', body: patch })
}
