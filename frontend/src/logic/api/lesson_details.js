// Детализация уроков репетитора за период: для хронологии.
import { apiFetch, withQuery } from './client.js'

export function getTutorLessonDetails({ dateFrom, dateTo, studentIds } = {}) {
  return apiFetch(
    withQuery('/api/v1/tutor/lessons/details', {
      date_from: dateFrom,
      date_to: dateTo,
      student_ids: studentIds && studentIds.length ? studentIds.join(',') : undefined,
    }),
  )
}
