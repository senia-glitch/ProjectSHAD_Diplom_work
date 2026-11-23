// Ученики, репетиторы, связи и слоты доступности
// (страницы репетиторов, учеников, расписания).
import { defineStore } from 'pinia'

export const useRosterStore = defineStore('roster', {
  state: () => ({ students: [], tutors: [], configurations: [], slots: [] }),
  actions: {
    setStudents(students) {
      this.students = students || []
    },
    setTutors(tutors) {
      this.tutors = tutors || []
    },
    setConfigurations(configurations) {
      this.configurations = configurations || []
    },
    setSlots(slots) {
      this.slots = slots || []
    },
  },
})
