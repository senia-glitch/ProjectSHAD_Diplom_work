// Данные страницы расписания: уроки, участники, ученики, настройки.
import { defineStore } from 'pinia'

export const useScheduleStore = defineStore('schedule', {
  state: () => ({
    lessons: [],
    participantsByLesson: {},
    tutorSettings: null,
    studentSettings: null,
    backgroundBookings: [],
    studentWindows: [],
  }),
  actions: {
    setLessons(lessons) {
      this.lessons = lessons || []
    },
    addLesson(lesson) {
      this.lessons = [...this.lessons, lesson]
    },
    updateLessonInList(lessonId, patch) {
      this.lessons = this.lessons.map((x) => (x.lesson_id === lessonId ? { ...x, ...patch } : x))
    },
    removeLessonFromList(lessonId) {
      this.lessons = this.lessons.filter((x) => x.lesson_id !== lessonId)
      const rest = { ...this.participantsByLesson }
      delete rest[lessonId]
      this.participantsByLesson = rest
    },
    setParticipants(lessonId, participants) {
      this.participantsByLesson = { ...this.participantsByLesson, [lessonId]: participants || [] }
    },
    setTutorSettings(settings) {
      this.tutorSettings = settings ?? null
    },
    setStudentSettings(settings) {
      this.studentSettings = settings ?? null
    },
    setBackgroundBookings(bookings) {
      this.backgroundBookings = bookings || []
    },
    setStudentWindows(windows) {
      this.studentWindows = windows || []
    },
  },
})
