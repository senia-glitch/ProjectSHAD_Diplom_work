// Статистика репетитора: выручка, часы, загрузка.
import { apiFetch, withQuery } from './client.js'

export function getTutorStatistics({ year, dateFrom, dateTo, granularity, studentIds } = {}) {
  return apiFetch(
    withQuery('/api/v1/tutor/statistics', {
      year,
      date_from: dateFrom,
      date_to: dateTo,
      granularity,
      student_ids: studentIds && studentIds.length ? studentIds.join(',') : undefined,
    }),
  )
}
