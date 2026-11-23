// Данные страницы броней.
import { defineStore } from 'pinia'

export const useBookingsStore = defineStore('bookings', {
  state: () => ({ bookings: [] }),
  actions: {
    setBookings(bookings) {
      this.bookings = bookings || []
    },
    addBooking(booking) {
      this.bookings = [...this.bookings, booking]
    },
    updateBookingInList(id, patch) {
      this.bookings = this.bookings.map((b) => (b.id === id ? { ...b, ...patch } : b))
    },
    removeBookingFromList(id) {
      this.bookings = this.bookings.filter((b) => b.id !== id)
    },
  },
})
