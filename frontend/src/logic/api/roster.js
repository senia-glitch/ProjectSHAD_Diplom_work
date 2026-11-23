// Ученики репетитора.
import { apiFetch } from './client.js'

export function getTutorStudents() {
  return apiFetch('/api/v1/tutor/students')
}
