// Связи ученик–репетитор: ветки обеих ролей.
import { apiFetch } from './client.js'
import { absenceToUser } from '../utils/tz.js'

export function listTutorConfigurations() {
  return apiFetch('/api/v1/tutor/configurations')
}

export function getTutorConfiguration(configId) {
  return apiFetch(`/api/v1/tutor/configurations/${configId}`)
}

export function createTutorConfigurationByCode({ personalNumber }) {
  return apiFetch('/api/v1/tutor/configurations/by-code', {
    method: 'POST',
    body: { personal_number: personalNumber },
  })
}

export function updateTutorConfiguration(configId, patch) {
  return apiFetch(`/api/v1/tutor/configurations/${configId}`, {
    method: 'PATCH',
    body: patch,
  })
}

export function resetTutorConfiguration(configId) {
  return apiFetch(`/api/v1/tutor/configurations/${configId}/reset`, { method: 'POST' })
}

export function deleteTutorConfiguration(configId) {
  return apiFetch(`/api/v1/tutor/configurations/${configId}`, { method: 'DELETE' })
}

export function listStudentConfigurations() {
  return apiFetch('/api/v1/student/configurations')
}

export async function getStudentConfiguration(configId) {
  const data = await apiFetch(`/api/v1/student/configurations/${configId}`)
  return data && data.tutor_absence ? { ...data, tutor_absence: absenceToUser(data.tutor_absence) } : data
}

export function createStudentConfigurationByCode({ personalNumber }) {
  return apiFetch('/api/v1/student/configurations/by-code', {
    method: 'POST',
    body: { personal_number: personalNumber },
  })
}

export function deleteStudentConfiguration(configId) {
  return apiFetch(`/api/v1/student/configurations/${configId}`, { method: 'DELETE' })
}

// Заявки на связь: ответ второй стороны.
export function acceptTutorConfiguration(configId) {
  return apiFetch(`/api/v1/tutor/configurations/${configId}/accept`, { method: 'POST' })
}

export function declineTutorConfiguration(configId) {
  return apiFetch(`/api/v1/tutor/configurations/${configId}/decline`, { method: 'POST' })
}

export function acceptStudentConfiguration(configId) {
  return apiFetch(`/api/v1/student/configurations/${configId}/accept`, { method: 'POST' })
}

export function declineStudentConfiguration(configId) {
  return apiFetch(`/api/v1/student/configurations/${configId}/decline`, { method: 'POST' })
}
