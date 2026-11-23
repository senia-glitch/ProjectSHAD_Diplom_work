// Данные страницы управления.
import { defineStore } from 'pinia'

export const useAdminStore = defineStore('admin', {
  state: () => ({ users: [], currentUser: null, students: [], tutors: [], admins: [] }),
  actions: {
    setUsers(users) {
      this.users = users || []
    },
    setCurrentUser(user) {
      this.currentUser = user ?? null
    },
    updateUserInList(userId, patch) {
      this.users = this.users.map((u) => (u.user_id === userId ? { ...u, ...patch } : u))
      if (this.currentUser?.user_id === userId) {
        this.currentUser = { ...this.currentUser, ...patch }
      }
    },
    setStudents(students) {
      this.students = students || []
    },
    setTutors(tutors) {
      this.tutors = tutors || []
    },
    setAdmins(admins) {
      this.admins = admins || []
    },
  },
})
