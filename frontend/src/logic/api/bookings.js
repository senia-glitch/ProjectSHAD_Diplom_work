// Брони репетитора.
import { apiFetch, withQuery } from './client.js'

// Нормализация транспорта в доменную форму: у брони сквозной id.
function toBookingShape(raw) {
  return { ...raw, id: raw.booking_id }
}

export function getMyBookings({ weekday, limit, offset } = {}) {
  return apiFetch(withQuery('/api/v1/tutor/me/bookings', { weekday, limit, offset })).then((data) => ({
    ...data,
    bookings: (data.bookings || []).map(toBookingShape),
  }))
}

export function createBooking({ weekday, startTime, endTime, accessRule, accessTargets }) {
  const body = { weekday, start_time: startTime, end_time: endTime, access_rule: accessRule }
  if (accessTargets !== undefined) body.access_targets = accessTargets
  return apiFetch('/api/v1/tutor/bookings', { method: 'POST', body }).then(toBookingShape)
}

export function patchBooking(bookingId, patch) {
  return apiFetch(`/api/v1/tutor/bookings/${bookingId}`, { method: 'PATCH', body: patch }).then(
    toBookingShape,
  )
}

export function deleteBooking(bookingId) {
  return apiFetch(`/api/v1/tutor/bookings/${bookingId}`, { method: 'DELETE' })
}
