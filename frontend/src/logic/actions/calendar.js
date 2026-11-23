// Сценарии страницы календаря: уроки за диапазон по роли.
import { getTutorLessons, getStudentLessons } from '../api/index.js'
import { useAuthStore } from '../store/index.js'

export async function loadCalendarLessons({ dateFrom, dateTo }) {
  const role = useAuthStore().role
  const data = role === 'student'
    ? await getStudentLessons({ dateFrom, dateTo })
    : await getTutorLessons({ dateFrom, dateTo })
  return data.lessons || []
}
