// Сценарии страницы календаря: уроки за диапазон по роли.
import { getTutorLessons, getStudentLessons, getLessonParticipants } from '../api/index.js'
import { upcomingRange, userNowIso } from '../utils/index.js'
import { useAuthStore } from '../store/index.js'

export async function loadCalendarLessons({ dateFrom, dateTo }) {
  const role = useAuthStore().role
  const data = role === 'student'
    ? await getStudentLessons({ dateFrom, dateTo })
    : await getTutorLessons({ dateFrom, dateTo })
  return data.lessons || []
}

// «Ближайшие уроки»: неделя вперёд + месяц истории отмен. Репетитору — с участниками.
export async function loadUpcomingLessons() {
  const role = useAuthStore().role
  const lessons = await loadCalendarLessons(upcomingRange(userNowIso()))
  if (role !== 'tutor') return lessons
  const now = userNowIso()
  const soon = lessons.filter((l) => ['PENDING', 'SCHEDULED', 'ONGOING'].includes(l.status) && l.end_time > now)
  const withPeople = await Promise.all(soon.map(async (l) => {
    try {
      const data = await getLessonParticipants(l.lesson_id)
      return [l.lesson_id, data.participants || []]
    } catch {
      return [l.lesson_id, []]
    }
  }))
  const byId = Object.fromEntries(withPeople)
  return lessons.map((l) => (byId[l.lesson_id] ? { ...l, participants: byId[l.lesson_id] } : l))
}
