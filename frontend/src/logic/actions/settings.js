// Сценарии страниц настроек репетитора и ученика.
import {
  getTutorProfile,
  patchTutorSettings,
  getStudentProfile,
  patchStudentSettings,
} from '../api/index.js'

export async function loadTutorProfile() {
  return getTutorProfile()
}

export async function saveTutorSettings(patch) {
  return patchTutorSettings(patch)
}

export async function loadStudentProfile() {
  return getStudentProfile()
}

export async function saveStudentSettings(patch) {
  return patchStudentSettings(patch)
}
