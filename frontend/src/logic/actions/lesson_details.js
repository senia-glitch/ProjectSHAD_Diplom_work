// Детализация уроков: сквозная загрузка без записи в store
// (переходный набор для хронологии и выгрузок).
import {
  getTutorLessonDetails,
  setLessonParticipantPaid,
  getTutorLesson,
  getStudentLesson,
  addLessonParticipant,
  removeLessonParticipant,
  patchTutorLesson,
} from '../api/index.js'
import { useAuthStore } from '../store/index.js'

export async function loadLessonDetails(filters = {}) {
  const data = await getTutorLessonDetails(filters)
  return data.lessons || []
}

// Полная детализация: уроки + счётчики отмен записей по инициаторам.
// Нужно динамике: сами отменённые записи details прячет.
export async function loadLessonDetailsFull(filters = {}) {
  const f = { ...filters }
  if (!f.dateFrom || !f.dateTo) {
    const now = new Date()
    const year = now.getFullYear()
    f.dateFrom = `${year}-01-01`
    f.dateTo = `${year}-12-31`
  }
  const data = await getTutorLessonDetails(f)
  return {
    lessons: data.lessons || [],
    cancelledByStudent: data.cancelled_by_student || 0,
    cancelledByTutor: data.cancelled_by_tutor || 0,
  }
}

export async function setParticipantPaid(lessonId, studentUserId, paid) {
  const res = await setLessonParticipantPaid(lessonId, studentUserId, paid)
  return res?.paid ?? Boolean(paid)
}

// Один урок по id: ветка роли. Чужой/несуществующий — 404 с бэкенда.
export async function loadLessonById(lessonId) {
  const role = useAuthStore().role
  return role === 'student' ? getStudentLesson(lessonId) : getTutorLesson(lessonId)
}

export async function addParticipantToLesson(lessonId, studentUserId) {
  return addLessonParticipant(lessonId, { studentUserId })
}

export async function removeParticipantFromLesson(lessonId, studentUserId) {
  return removeLessonParticipant(lessonId, studentUserId)
}

// Ссылки урока (видео-звонок, материалы, доска): репетитор сохраняет весь список целиком.
export async function saveLessonLinks(lessonId, links) {
  return patchTutorLesson(lessonId, { lesson_links: links })
}

// Отметка урока репетитором: FINISHED (проведён), NO_SHOW (неявка), CANCELLED (отмена) — с причиной.
export async function saveLessonStatus(lessonId, status, reason) {
  return patchTutorLesson(lessonId, { status, reason: reason || null })
}
