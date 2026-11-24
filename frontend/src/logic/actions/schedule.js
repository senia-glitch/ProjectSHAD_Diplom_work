// Сценарии страницы расписания.
import {
  getTutorLessons,
  createTutorLesson,
  patchTutorLesson,
  deleteTutorLesson,
  getStudentLessons,
  createStudentLesson,
  getStudentAvailableSlots,
  getLessonParticipants,
  addLessonParticipant,
  removeLessonParticipant,
  getMyBookings,
  getTutorProfile,
  getStudentProfile,
  cancelStudentLesson,
  confirmTutorLesson,
  rejectTutorLesson,
} from '../api/index.js'
import { useScheduleStore, useAuthStore } from '../store/index.js'
import { nextSeq, isCurrentSeq } from './loading.js'

export async function loadScheduleLessons() {
  const my = nextSeq('scheduleLessons')
  const store = useScheduleStore()
  const role = useAuthStore().role
  // Лимит 1000: роуты уроков имеют дефолт limit=100 с сортировкой по
  // start_time ASC — сетка расписания получала только первые 100 самых
  // старых уроков (актуальная неделя пропадала после ~100 записей).
  const data =
    role === 'student'
      ? await getStudentLessons({ limit: 1000 })
      : await getTutorLessons({ limit: 1000 })
  if (!isCurrentSeq('scheduleLessons', my)) return
  store.setLessons(data.lessons || [])
}

export async function loadScheduleSettings() {
  const my = nextSeq('scheduleSettings')
  const data = await getTutorProfile()
  if (!isCurrentSeq('scheduleSettings', my)) return
  useScheduleStore().setTutorSettings(data)
}

export async function loadStudentScheduleSettings() {
  const my = nextSeq('studentScheduleSettings')
  const data = await getStudentProfile()
  if (!isCurrentSeq('studentScheduleSettings', my)) return
  useScheduleStore().setStudentSettings(data)
}

export async function loadBackgroundBookings() {
  const my = nextSeq('backgroundBookings')
  const data = await getMyBookings({ limit: 1000 })
  if (!isCurrentSeq('backgroundBookings', my)) return
  useScheduleStore().setBackgroundBookings(data.bookings || [])
}

export async function loadLessonParticipants(lessonId) {
  // Не бросает. Сеть — пустой список; HTTP-ошибка — старые данные как были.
  try {
    const data = await getLessonParticipants(lessonId)
    useScheduleStore().setParticipants(lessonId, data.participants || [])
  } catch (e) {
    if (!e.status) useScheduleStore().setParticipants(lessonId, [])
  }
}

export async function createLessonsFromPreview(items, { isGroup, participantIds }) {
  // Строго последовательно, сбои не прерывают список. Возвращает
  // созданные id и сырые сбои; тексты для пользователя форматирует компонент.
  const store = useScheduleStore()
  const lessonIds = []
  const failed = []
  for (const item of items) {
    let lesson = null
    try {
      lesson = await createTutorLesson({
        startTime: item.start,
        endTime: item.end,
        isGroup,
      })
    } catch (e) {
      failed.push({
        start: item.start,
        end: item.end,
        kind: 'lesson',
        network: !e.status,
        payload: e.payload,
        message: e.message,
      })
      continue
    }
    store.addLesson(lesson)
    lessonIds.push(lesson.lesson_id)
    for (const uid of participantIds) {
      try {
        await addLessonParticipant(lesson.lesson_id, { studentUserId: uid })
      } catch (e) {
        failed.push({
          start: item.start,
          end: item.end,
          kind: 'participant',
          uid,
          network: !e.status,
          payload: e.payload,
          message: e.message,
        })
      }
    }
  }
  return { created: lessonIds.length, lessonIds, failed }
}

export async function updateLessonWithParticipants(lessonId, { timePatch, originalIds, currentIds }) {
  // PATCH времён, затем дифф участников, затем перезагрузка с сервера.
  // Сбои — сырыми записями { uid, op, message }.
  const store = useScheduleStore()
  const updated = await patchTutorLesson(lessonId, timePatch)
  store.updateLessonInList(lessonId, updated)

  const orig = new Set(originalIds)
  const curr = new Set(currentIds)
  const failed = []
  for (const uid of [...curr].filter((id) => !orig.has(id))) {
    try {
      await addLessonParticipant(lessonId, { studentUserId: uid })
    } catch (e) {
      failed.push({ uid, op: 'add', network: !e.status, payload: e.payload, message: e.message })
    }
  }
  for (const uid of [...orig].filter((id) => !curr.has(id))) {
    try {
      await removeLessonParticipant(lessonId, uid)
    } catch (e) {
      failed.push({ uid, op: 'remove', network: !e.status, payload: e.payload, message: e.message })
    }
  }
  await loadLessonParticipants(lessonId)
  return { failed }
}

export async function deleteLesson(lessonId) {
  await deleteTutorLesson(lessonId)
  useScheduleStore().removeLessonFromList(lessonId)
}

// Кэш окон по ключу репетитор+диапазон: хранит окна одного запроса,
// в store они мержатся поверх старых записей того же репетитора.
// Инвалидация — созданием урока (см. ниже).
const windowsCache = new Map()

// Полная очистка кэша окон (например, при logout, чтобы окна
// предыдущего пользователя не пережили сессию).
export function clearScheduleCaches() {
  windowsCache.clear()
}

export async function loadStudentWindows({ tutorUserId, tutorName, dateFrom, dateTo }) {
  const store = useScheduleStore()
  const rangeKey = `${dateFrom}|${dateTo}`
  const key = `${tutorUserId}|${rangeKey}`
  // Seq-ключ на пару репетитор+диапазон: параллельные загрузки окон
  // разных репетиторов (и «неделя» + «диапазон формы») не затирают
  // друг друга, устаревший ответ одного ключа отбрасывается локально.
  const seqKey = `studentWindows:${key}`
  const my = nextSeq(seqKey)
  let own = windowsCache.get(key)
  if (!own) {
    const data = await getStudentAvailableSlots({ tutorUserId, dateFrom, dateTo })
    if (!isCurrentSeq(seqKey, my)) return store.studentWindows
    own = (data.slots || []).map((s) => ({
      tutorUserId,
      tutorName: tutorName || '',
      rangeKey,
      start: s.start,
      end: s.end,
    }))
    windowsCache.set(key, own)
  }
  if (!isCurrentSeq(seqKey, my)) return store.studentWindows
  // Заменяем только записи этого репетитора за этот диапазон
  // (видимая неделя и диапазон формы живут рядом, не затирая друг друга).
  const rest = store.studentWindows.filter(
    (w) => w.tutorUserId !== tutorUserId || (w.rangeKey && w.rangeKey !== rangeKey),
  )
  const merged = [...rest, ...own]
  store.setStudentWindows(merged)
  return merged
}

// Оставить в store только окна репетиторов из живых форм.
// Вызывать при удалении/смене репетитора в форме и при уходе
// со страницы: иначе подсветка переживает свои формы.
export function pruneStudentWindows(keepTutorUserIds) {
  const keep = new Set(keepTutorUserIds || [])
  const store = useScheduleStore()
  store.setStudentWindows(store.studentWindows.filter((w) => keep.has(w.tutorUserId)))
}

export function clearStudentWindows() {
  useScheduleStore().setStudentWindows([])
}

export async function createStudentLessonsFromPreview(items, { tutorUserId }) {
  // Строго последовательно, сбои не прерывают список. Возвращает
  // созданные id и сырые сбои; тексты форматирует компонент.
  const store = useScheduleStore()
  const lessonIds = []
  const failed = []
  for (const item of items) {
    try {
      const lesson = await createStudentLesson({
        tutorUserId,
        startTime: item.start,
        endTime: item.end,
      })
      store.addLesson(lesson)
      lessonIds.push(lesson.lesson_id)
    } catch (e) {
      failed.push({
        start: item.start,
        end: item.end,
        kind: 'lesson',
        network: !e.status,
        payload: e.payload,
        message: e.message,
      })
    }
  }
  if (lessonIds.length) {
    windowsCache.clear()
    await loadScheduleLessons()
  }
  return { created: lessonIds.length, lessonIds, failed }
}

// Ученик отменяет урок (или отзывает заявку) с необязательной причиной.
// Освободившееся время сразу видно в окнах: кэш окон сбрасывается.
export async function cancelLessonAsStudent(lessonId, reason) {
  await cancelStudentLesson(lessonId, reason)
  windowsCache.clear()
  await loadScheduleLessons()
}

// Репетитор решает заявку ученика.
export async function confirmLessonRequest(lessonId, reason) {
  const result = await confirmTutorLesson(lessonId, reason)
  await loadScheduleLessons()
  return result
}

export async function rejectLessonRequest(lessonId, reason) {
  const result = await rejectTutorLesson(lessonId, reason)
  await loadScheduleLessons()
  return result
}
