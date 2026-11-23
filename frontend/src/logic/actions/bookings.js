// Сценарии страницы броней.
import {
  getMyBookings,
  createBooking as apiCreateBooking,
  patchBooking as apiPatchBooking,
  deleteBooking as apiDeleteBooking,
} from '../api/index.js'
import { ruleRequiresTargets } from '../constants/index.js'
import { useBookingsStore } from '../store/index.js'
import { nextSeq, isCurrentSeq } from './loading.js'

export async function loadBookings() {
  const my = nextSeq('bookings')
  const data = await getMyBookings()
  if (!isCurrentSeq('bookings', my)) return
  useBookingsStore().setBookings(data.bookings || [])
}

export async function createBookings(slots) {
  // Последовательно, остановка на первой HTTP-ошибке (как было).
  // Сеть — исключением наверх. Возвращает итог вместо throw,
  // чтобы компонент показал номер слота как раньше.
  const store = useBookingsStore()
  const items = []
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i]
    try {
      const createdBooking = await apiCreateBooking({
        weekday: slot.weekday,
        startTime: slot.start_time,
        endTime: slot.end_time,
        accessRule: slot.access_rule,
        accessTargets: ruleRequiresTargets(slot.access_rule) ? slot.access_targets : null,
      })
      store.addBooking(createdBooking)
      items.push(createdBooking)
    } catch (e) {
      if (!e.status) throw e
      return { created: items.length, items, error: { message: e.message, slotIndex: i, status: e.status, payload: e.payload } }
    }
  }
  return { created: items.length, items, error: null }
}

export async function updateBooking(bookingId, form) {
  const updated = await apiPatchBooking(bookingId, {
    weekday: form.weekday,
    start_time: form.start_time,
    end_time: form.end_time,
    access_rule: form.access_rule,
    access_targets: ruleRequiresTargets(form.access_rule) ? form.access_targets : null,
  })
  useBookingsStore().updateBookingInList(bookingId, updated)
  return updated
}

export async function deleteBooking(bookingId) {
  await apiDeleteBooking(bookingId)
  useBookingsStore().removeBookingFromList(bookingId)
}
