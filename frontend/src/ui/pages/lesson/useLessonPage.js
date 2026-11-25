// Состояние страницы урока: загрузка по id, вход на занятие (фаза и отсчёт),
// ссылки и доска, отметки репетитора, участники и оплаты. Роль определяет ветку данных.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  loadLessonById,
  setParticipantPaid,
  addParticipantToLesson,
  removeParticipantFromLesson,
  deleteLesson,
  loadTutorStudents,
  loadStudentTutors,
  cancelLessonAsStudent,
  confirmLessonRequest,
  rejectLessonRequest,
  saveLessonLinks,
  saveLessonStatus,
  openLessonBoard,
} from '../../../logic/actions/index.js'
import { useRosterStore, useAuthStore } from '../../../logic/store/index.js'
import { logError } from '../../../logic/logger/index.js'
import {
  lessonPhase, lessonSafeLinks, lessonLinksVisible, lessonLinksRemainingMin, boardIdFromLink, userNowMs,
} from '../../../logic/utils/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'

const TICK_MS = 30000

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
  const boardOpening = ref(false)
  const nowMs = ref(userNowMs())

  const isTutor = computed(() => authStore.role === 'tutor')
  const roster = computed(() => (isTutor.value ? rosterStore.students : rosterStore.tutors))

  // ----- вход на занятие -----
  const phase = computed(() => lessonPhase(lesson.value, nowMs.value))
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  // Репетитору сервер отдаёт ссылки в links, ученику — в lesson_links.
  const links = computed(() => lessonSafeLinks(lesson.value?.links || lesson.value?.lesson_links).map((l) => {
    const boardId = boardIdFromLink(l.safe, origin)
    return { ...l, boardId, to: boardId ? `/boards/${boardId}` : null }
  }))
  // Настройки показа ссылок ученику — из связи с репетитором (как в расписании).
  const linkConfig = computed(() => (isTutor.value ? null : rosterStore.tutors.find((t) => t.tutor_id === lesson.value?.tutor_id) || null))
  const linksVisible = computed(() => isTutor.value || !lesson.value || lessonLinksVisible(linkConfig.value, lesson.value.start_time, nowMs.value))
  const linksInMinutes = computed(() => (linksVisible.value ? 0 : lessonLinksRemainingMin(linkConfig.value, lesson.value.start_time, nowMs.value)))

  async function reload() {
    loading.value = !lesson.value
    error.value = ''
    try {
      lesson.value = await loadLessonById(lessonId.value)
    } catch (e) {
      if (!e.status) error.value = 'Ошибка сети'
      else if (e.status === 404) error.value = 'Урок не найден или недоступен'
      else error.value = e.message || 'Не удалось загрузить урок'
      logError('lesson', 'load:error', { error: e.message })
    } finally {
      loading.value = false
    }
  }

  async function run(action, okText, logKey) {
    busy.value = true
    try {
      await action()
      await reload()
      if (okText) toast(okText, 'ok')
      return true
    } catch (e) {
      toast(e.message || 'Не удалось сохранить', 'error')
      logError('lesson', `${logKey}:error`, { error: e.message })
      return false
    } finally {
      busy.value = false
    }
  }

  const togglePaid = (student) => run(() => setParticipantPaid(lessonId.value, student.student_user_id, !student.paid), '', 'pay')

  async function addParticipant() {
    if (!newParticipant.value) return
    if (await run(() => addParticipantToLesson(lessonId.value, Number(newParticipant.value)), 'Ученик добавлен', 'add-participant')) {
      newParticipant.value = ''
    }
  }

  async function removeParticipant(student) {
    const ok = await askConfirm(`Убрать ${student.student_name} с урока?`, 'Запись ученика будет отменена репетитором.', { okText: 'Убрать', danger: true })
    if (ok) await run(() => removeParticipantFromLesson(lessonId.value, student.student_user_id), 'Ученик убран с урока', 'remove-participant')
  }

  async function handleDelete() {
    const ok = await askConfirm('Удалить урок?', 'Урок и все записи на него будут удалены безвозвратно. Для обычной отмены используйте «Отменить урок» — тогда ученики получат уведомление, а урок останется в истории.', { okText: 'Удалить', danger: true })
    if (!ok) return
    busy.value = true
    try {
      await deleteLesson(lessonId.value)
      router.push('/schedule')
    } catch (e) {
      toast(e.message || 'Не удалось удалить', 'error')
      logError('lesson', 'delete:error', { error: e.message })
      busy.value = false
    }
  }

  // ----- доска урока и ссылки -----
  const rawLinks = () => (lesson.value?.links || []).map((l) => ({ alias: l.alias || '', url: l.url || '' }))

  // Своя доска у каждого урока: создаётся при первом открытии, входят без кода.
  async function openBoard() {
    boardOpening.value = true
    try {
      const board = await openLessonBoard(lessonId.value)
      router.push(`/boards/${board.id}`)
    } catch (e) {
      toast(e.message || 'Не удалось открыть доску урока', 'error')
      logError('lesson', 'board:error', { error: e.message })
    } finally {
      boardOpening.value = false
    }
  }

  async function removeLink(link) {
    const ok = await askConfirm(`Убрать ссылку «${link.alias}»?`, 'Ссылка исчезнет из урока у всех участников.', { okText: 'Убрать', danger: true })
    if (!ok) return
    const rest = rawLinks().filter((l) => !(l.url === link.url && (l.alias || 'Ссылка') === link.alias))
    await run(() => saveLessonLinks(lessonId.value, rest), 'Ссылка убрана', 'remove-link')
  }

  // ----- решения с причиной: ошибку показывает диалог -----
  const decisionError = ref('')

  async function decide(action, reason) {
    busy.value = true
    decisionError.value = ''
    try {
      await action(lessonId.value, reason)
      await reload()
      return true
    } catch (e) {
      decisionError.value = e.message || 'Не удалось сохранить'
      logError('lesson', 'decision:error', { error: e.message })
      return false
    } finally {
      busy.value = false
    }
  }

  const cancelAsStudent = (reason) => decide(cancelLessonAsStudent, reason)
  const confirmRequest = () => decide(confirmLessonRequest, '')
  const rejectRequest = (reason) => decide(rejectLessonRequest, reason)
  const markStatus = (status, reason) => decide((id, r) => saveLessonStatus(id, status, r), reason)

  let timer = 0
  onMounted(async () => {
    timer = setInterval(() => { nowMs.value = userNowMs() }, TICK_MS)
    try {
      if (isTutor.value) await loadTutorStudents()
      else await loadStudentTutors()
    } catch (e) {
      logError('lesson', 'roster:error', { error: e.message })
    }
    await reload()
  })
  onBeforeUnmount(() => clearInterval(timer))

  return {
    lessonId, lesson, loading, error, busy, isTutor, roster, newParticipant, boardOpening,
    phase, links, linksVisible, linksInMinutes,
    togglePaid, addParticipant, removeParticipant, handleDelete, openBoard, removeLink,
    decisionError, cancelAsStudent, confirmRequest, rejectRequest, markStatus,
  }
}
