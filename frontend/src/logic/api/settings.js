// Профиль и настройки репетитора и ученика.
// Период отсутствия (отпуск/болезнь) на границе переводится между UTC и поясом пользователя.
import { apiFetch } from './client.js'
import { toServerTime, toUserTime } from '../utils/tz.js'

function absenceToUser(data) {
  if (!data) return data
  return { ...data, absence_from: toUserTime(data.absence_from), absence_to: toUserTime(data.absence_to) }
}

export async function getTutorProfile() {
  return absenceToUser(await apiFetch('/api/v1/tutor/me'))
}

export async function patchTutorSettings(patch) {
  const body = { ...patch }
  for (const key of ['absence_from', 'absence_to']) {
    if (body[key]) body[key] = toServerTime(body[key])
  }
  return absenceToUser(await apiFetch('/api/v1/tutor/me/settings', { method: 'PATCH', body }))
}

export function getStudentProfile() {
  return apiFetch('/api/v1/student/me')
}

export function patchStudentSettings(patch) {
  return apiFetch('/api/v1/student/me/settings', { method: 'PATCH', body: patch })
}
