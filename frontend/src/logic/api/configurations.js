// Связи ученик–репетитор: ветки обеих ролей.
import { apiFetch } from './client.js'

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

export function getStudentConfiguration(configId) {
  return apiFetch(`/api/v1/student/configurations/${configId}`)
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
