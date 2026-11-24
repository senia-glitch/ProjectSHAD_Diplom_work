// Сценарии страниц настроек репетитора и ученика.
import {
  getTutorProfile,
  patchTutorSettings,
  getStudentProfile,
  patchStudentSettings,
} from '../api/index.js'
import { useAuthStore } from '../store/index.js'

// Смена личного пояса сразу меняет показ времени во всём приложении.
function rememberOffset(saved) {
  const auth = useAuthStore()
  if (saved && typeof saved.timezone_offset === 'number' && auth.user) {
    auth.setUser({ ...auth.user, timezone_offset: saved.timezone_offset })
  }
  return saved
}

export async function loadTutorProfile() {
  return getTutorProfile()
}

export async function saveTutorSettings(patch) {
  return rememberOffset(await patchTutorSettings(patch))
}

export async function loadStudentProfile() {
  return getStudentProfile()
}

export async function saveStudentSettings(patch) {
  return rememberOffset(await patchStudentSettings(patch))
}
