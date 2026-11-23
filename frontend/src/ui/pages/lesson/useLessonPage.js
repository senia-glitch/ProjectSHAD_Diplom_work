// Состояние страницы урока: загрузка по id, действия с участниками,
// удаление. Роль определяет ветку данных.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  loadLessonById,
  setParticipantPaid,
  addParticipantToLesson,
  removeParticipantFromLesson,
  deleteLesson,
  loadTutorStudents,
  loadStudentTutors,
} from '../../../logic/actions/index.js'
import { useRosterStore, useAuthStore } from '../../../logic/store/index.js'
import { logError } from '../../../logic/logger/index.js'

export function useLessonPage() {
  const route = useRoute()
  const router = useRouter()
  const authStore = useAuthStore()
  const rosterStore = useRosterStore()

  const lessonId = computed(() => Number(route.params.id))
  const lesson = ref(null)
  const loading = ref(true)
  const error = ref('')
  const busy = ref(false)
  const newParticipant = ref('')

  const isTutor = computed(() => authStore.role === 'tutor')
  const roster = computed(() => (isTutor.value ? rosterStore.students : rosterStore.tutors))

  async function reload() {
    loading.value = true
    error.value = ''
    try {
      lesson.value = await loadLessonById(lessonId.value)
    } catch (e) {
      if (!e.status) error.value = 'Ошибка сети'
      else if (e.status === 404) error.value = 'Урок не найден или недоступен'
      else error.value = e.payload?.error?.message || e.message || 'Не удалось загрузить урок'
      logError('lesson', 'load:error', { error: e.message })
    } finally {
      loading.value = false
    }
  }

  async function togglePaid(student) {
    busy.value = true
    try {
      await setParticipantPaid(lessonId.value, student.student_user_id, !student.paid)
      await reload()
    } catch (e) {
      logError('lesson', 'pay:error', { error: e.message })
    } finally {
      busy.value = false
    }
  }

  async function addParticipant() {
    if (!newParticipant.value) return
    busy.value = true
    try {
      await addParticipantToLesson(lessonId.value, Number(newParticipant.value))
      newParticipant.value = ''
      await reload()
    } catch (e) {
      logError('lesson', 'add-participant:error', { error: e.message })
    } finally {
      busy.value = false
    }
  }

  async function removeParticipant(student) {
    busy.value = true
    try {
      await removeParticipantFromLesson(lessonId.value, student.student_user_id)
      await reload()
    } catch (e) {
      logError('lesson', 'remove-participant:error', { error: e.message })
    } finally {
      busy.value = false
    }
  }

  async function handleDelete() {
    if (!window.confirm('Удалить урок со всеми участниками?')) return
    busy.value = true
    try {
      await deleteLesson(lessonId.value)
      router.push('/schedule')
    } catch (e) {
      logError('lesson', 'delete:error', { error: e.message })
      busy.value = false
    }
  }

  onMounted(async () => {
    try {
      if (isTutor.value) await loadTutorStudents()
      else await loadStudentTutors()
    } catch (e) {
      logError('lesson', 'roster:error', { error: e.message })
    }
    await reload()
  })

  return {
    lessonId, lesson, loading, error, busy, isTutor, roster, newParticipant,
    togglePaid, addParticipant, removeParticipant, handleDelete,
  }
}
