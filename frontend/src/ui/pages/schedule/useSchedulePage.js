// UI-логика страницы расписания: выбор, редактирование, сетка, монтирование.
// Сеть — только через actions, состояние предметной области — в store.
// Формы создания живут в LessonCreator (одно место использования).
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  loadScheduleLessons,
  loadScheduleSettings,
  loadBackgroundBookings,
  loadLessonParticipants,
  updateLessonWithParticipants,
  deleteLesson,
  loadTutorStudents,
  loadStudentTutors,
  loadStudentScheduleSettings,
  loadStudentWindows,
  pruneStudentWindows,
  clearStudentWindows,
  loadTutorConfiguration,
  updateTutorConfiguration,
  saveTutorSettings,
} from '../../../logic/actions/index.js'
import { logInfo, logError } from '../../../logic/logger/index.js'
import { useScheduleStore, useAuthStore, useRosterStore } from '../../../logic/store/index.js'
import {
  WD_SHORT,
  WEEKDAY_ORDER,
  DEFAULT_DISPLAY_FROM,
  DEFAULT_DISPLAY_TO,
  GRID_H,
  HOUR_CELL_H,
  TUTOR_COLORS,
  SLOT_STEP_DEFAULT,
} from '../../../logic/constants/index.js'
import { fmtDate, getWeekStart, previewItems, fmtPreview, resolveTutorColor, buildStudentPreview } from '../../../logic/utils/index.js'

export function useSchedulePage() {
  const scheduleStore = useScheduleStore()
  const authStore = useAuthStore()

  // Доменные данные — тонкие проекции store для проброса в компоненты.
  const lessons = computed(() => scheduleStore.lessons)
  const students = computed(() => useRosterStore().students)
  const tutors = computed(() => useRosterStore().tutors)
  const participantsMap = computed(() => scheduleStore.participantsByLesson)
  const dimBookings = computed(() => scheduleStore.backgroundBookings)
  const freeWindows = computed(() => scheduleStore.uniqueStudentWindows)
  const scheduleSettings = computed(() => {
    if (authStore.role === 'student') {
      return (
        scheduleStore.studentSettings || {
          display_time_from: DEFAULT_DISPLAY_FROM,
          display_time_to: DEFAULT_DISPLAY_TO,
        }
      )
    }
    return (
      scheduleStore.tutorSettings || {
        display_time_from: DEFAULT_DISPLAY_FROM,
        display_time_to: DEFAULT_DISPLAY_TO,
      }
    )
  })

  const selectedIds = ref(new Set())
  const currentDate = ref(new Date())
  const loading = ref(true)
  const saving = ref(false)

  const editingId = ref(null)
  const editForm = reactive({ start_time: '', end_time: '', is_group: false, lesson_links: [], status: '' })
  const editErrors = reactive({ start_time: '', end_time: '' })
  const editMsg = ref('')
  const editErr = ref('')

  const participantsLoading = reactive({})
  const participantsRequests = {}
  const editOriginal = ref([])
  const editRows = ref([])
  const editDirty = ref(false)
  let editRowSeq = 0

  // Массив форм создания. Фабрика и содержимое форм — в LessonCreator,
  // здесь только сам массив (для превью на сетке) и его очистка.
  // Очистка гасит и подсветку окон: пустые формы — пустая сетка.
  const createSlots = ref([])

  function clearCreateForm() {
    createSlots.value = []
    pruneStudentWindows([])
  }

  // --- Сетка недели ---
  const startHour = computed(() => {
    const parts = scheduleSettings.value.display_time_from.split(':').map(Number)
    return parts[0]
  })

  const endHour = computed(() => {
    const parts = scheduleSettings.value.display_time_to.split(':').map(Number)
    return parts[0]
  })

  const effectiveStartHour = computed(() => startHour.value)
  const effectiveEndHour = computed(() => {
    if (endHour.value <= startHour.value) return 23
    return endHour.value
  })

  const visibleHours = computed(() => {
    const hours = []
    for (let h = effectiveStartHour.value; h <= effectiveEndHour.value; h++) {
      hours.push(h)
    }
    return hours
  })

  const dynamicGridH = computed(() => visibleHours.value.length * HOUR_CELL_H || GRID_H)

  const weekDays = computed(() => {
    const start = getWeekStart(currentDate.value)
    const today = new Date()
    const todayStr = fmtDate(today)
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start)
      d.setDate(d.getDate() + i)
      return {
        date: fmtDate(d),
        name: WD_SHORT[d.getDay()],
        num: d.getDate(),
        isToday: fmtDate(d) === todayStr,
      }
    })
  })



  function prevWeek() {
    const d = new Date(currentDate.value)
    d.setDate(d.getDate() - 7)
    currentDate.value = d
    fetchWeekWindows()
  }

  function nextWeek() {
    const d = new Date(currentDate.value)
    d.setDate(d.getDate() + 7)
    currentDate.value = d
    fetchWeekWindows()
  }

  function goToday() {
    currentDate.value = new Date()
    fetchWeekWindows()
  }

  // Уроки из предпросмотра всех форм — на сетку.
  // Формы ученика (tutor_user_id) считает студенческий билдер
  // по окнам и шагу связи; только валидные попадают на сетку.
  const previewBlocks = computed(() => {
    const out = []
    for (const slot of createSlots.value) {
      if (slot.tutor_user_id) {
        const t = tutors.value.find((x) => x.tutor_user_id === slot.tutor_user_id)
        const step = t?.slot_step_minutes > 0 ? t.slot_step_minutes : SLOT_STEP_DEFAULT
        const wins = scheduleStore.uniqueStudentWindows.filter((w) => w.tutorUserId === slot.tutor_user_id)
        for (const it of buildStudentPreview(slot, wins, step).items) {
          if (!it.ok) continue
          out.push({ lesson_id: `pv-${slot.key}-${it.key}`, start_time: it.start, end_time: it.end })
        }
        continue
      }
      for (const it of previewItems(slot)) {
        out.push({ lesson_id: `pv-${slot.key}-${it.key}`, start_time: it.start, end_time: it.end })
      }
    }
    return out
  })

  // --- Ученик: цвета репетиторов и окна видимой недели ---
  // Цвет один на репетитора: назначается при первом выборе,
  // меняется пикером в форме. Окна недели грузятся при выборе
  // репетитора и при листании; диапазон формы — отдельно для проверки.
  const tutorColors = reactive({})
  const colorCursor = ref(0)

  function ensureTutorColor(tutorUserId) {
    if (!tutorUserId || tutorColors[tutorUserId]) return
    tutorColors[tutorUserId] = TUTOR_COLORS[colorCursor.value % TUTOR_COLORS.length].id
    colorCursor.value += 1
  }

  function setTutorColor(tutorUserId, colorId) {
    if (tutorUserId && TUTOR_COLORS.some((c) => c.id === colorId)) {
      tutorColors[tutorUserId] = colorId
    }
  }

  // Итоговые цвета: ручной выбор либо детерминированный по порядку
  // в списке связанных. Пустого результата нет — сетка всегда
  // цветная, даже если назначение при выборе не сработало.
  const resolvedTutorColors = computed(() => {
    const out = {}
    for (const t of tutors.value) {
      out[t.tutor_user_id] = resolveTutorColor(t.tutor_user_id, tutors.value, tutorColors)
    }
    for (const [uid, cid] of Object.entries(tutorColors)) {
      if (!out[uid] && TUTOR_COLORS.some((c) => c.id === cid)) out[uid] = cid
    }
    return out
  })

  const pickedTutorIds = computed(() => [
    ...new Set(createSlots.value.map((s) => s.tutor_user_id).filter(Boolean)),
  ])

  // Дни weekly-режима из живых форм (объединение): их свободные
  // окна на сетке получают обводку поверх обычной подсветки.
  const outlinedWeekdays = computed(() => {
    const out = new Set()
    for (const s of createSlots.value) {
      if (s.mode !== 'weekly') continue
      for (const d of WEEKDAY_ORDER) {
        if (s.weekdays?.[d]?.on) out.add(d)
      }
    }
    return [...out]
  })

  const weekRange = computed(() => {
    if (!weekDays.value.length) return { dateFrom: '', dateTo: '' }
    return { dateFrom: weekDays.value[0].date, dateTo: weekDays.value[6].date }
  })

  async function fetchWeekWindows() {
    if (authStore.role !== 'student') return
    const r = weekRange.value
    if (!r.dateFrom) return
    for (const uid of pickedTutorIds.value) {
      ensureTutorColor(uid)
      const t = tutors.value.find((x) => x.tutor_user_id === uid)
      try {
        await loadStudentWindows({
          tutorUserId: uid,
          tutorName: t?.full_name || '',
          dateFrom: r.dateFrom,
          dateTo: r.dateTo,
        })
      } catch (e) {
        logError('schedule', 'weekWindows:fail', { tutor: uid, error: e.message })
      }
    }
  }

  // --- Выбор и участники ---
  function clearSelection() {
    selectedIds.value = new Set()
    if (editingId.value) cancelEdit()
  }

  function studentName(userId) {
    const s = students.value.find((x) => x.user_id === userId)
    return s ? s.full_name : `#${userId}`
  }

  function toggleSelect(l, e) {
    const newSet = new Set(e.altKey ? selectedIds.value : [])
    if (newSet.has(l.lesson_id)) {
      newSet.delete(l.lesson_id)
      if (editingId.value === l.lesson_id) cancelEdit()
    } else {
      newSet.add(l.lesson_id)
      loadParticipants(l.lesson_id).catch((err) => {
        logError('schedule', 'participants:fail', { lesson: l.lesson_id, error: err?.message })
      })
    }
    selectedIds.value = newSet
  }

  async function loadParticipants(lessonId) {
    // Параллельные вызовы ждут текущий запрос, а не отваливаются.
    if (participantsRequests[lessonId]) {
      await participantsRequests[lessonId]
      return
    }
    participantsLoading[lessonId] = true
    try {
      participantsRequests[lessonId] = loadLessonParticipants(lessonId)
      await participantsRequests[lessonId]
    } finally {
      delete participantsRequests[lessonId]
      participantsLoading[lessonId] = false
    }
  }

  function syncEditRows(lessonId) {
    const current = participantsMap.value[lessonId] || []
    editOriginal.value = current.map((p) => p.student_user_id)
    editRows.value = editOriginal.value.map((uid) => ({ key: ++editRowSeq, student_user_id: uid }))
  }

  function addEditRow() {
    addParticipantErr.value = ''
    editRows.value = [...editRows.value, { key: ++editRowSeq, student_user_id: null }]
    editDirty.value = true
  }

  function removeEditRow(rowKey) {
    addParticipantErr.value = ''
    editRows.value = editRows.value.filter((r) => r.key !== rowKey)
    editDirty.value = true
  }

  function singlePick(uid) {
    addParticipantErr.value = ''
    editRows.value = uid ? [{ key: ++editRowSeq, student_user_id: uid }] : []
    editDirty.value = true
  }

  const addParticipantErr = ref('')

  // --- Ссылки урока ---
  function addEditLink() {
    if ((editForm.lesson_links || []).length >= 10) return
    editForm.lesson_links = [...(editForm.lesson_links || []), { alias: '', url: '' }]
  }

  function removeEditLink(index) {
    editForm.lesson_links = (editForm.lesson_links || []).filter((_, i) => i !== index)
  }

  function isHttpsUrl(url) {
    try {
      return new URL(url).protocol === 'https:'
    } catch {
      return false
    }
  }

  function cleanLinks(links) {
    return (links || [])
      .map((l) => ({ alias: (l.alias || '').trim(), url: (l.url || '').trim() }))
      .filter((l) => l.alias || l.url)
  }

  function validateLinks() {
    for (const l of cleanLinks(editForm.lesson_links)) {
      if (!l.alias || !l.url) return 'У ссылок должны быть название и адрес'
      if (!isHttpsUrl(l.url)) return 'Только https:// ссылки'
    }
    return ''
  }

  // Единственный участник редактируемого урока (profile id) —
  // только тогда доступны кнопки конфигурации.
  function singleConfigStudentId() {
    const list = editingId.value != null ? participantsMap.value[editingId.value] : null
    return Array.isArray(list) && list.length === 1 ? list[0].student_id : null
  }

  function singleConfig() {
    const sid = singleConfigStudentId()
    if (sid == null) return null
    return useRosterStore().configurations.find((c) => c.student_id === sid) || null
  }

  async function applyLinksFromSettings() {
    editErr.value = ''
    const links = useScheduleStore().tutorSettings?.default_links || []
    editForm.lesson_links = links.map((l) => ({ alias: l.alias || '', url: l.url || '' }))
  }

  async function applyLinksToSettings() {
    editErr.value = ''
    editMsg.value = ''
    try {
      await saveTutorSettings({ default_links: cleanLinks(editForm.lesson_links) })
      await loadScheduleSettings()
      editMsg.value = 'Сохранено в настройки'
      logInfo('schedule', 'linksToSettings:ok')
      setTimeout(() => { if (editMsg.value === 'Сохранено в настройки') editMsg.value = '' }, 3000)
    } catch (e) {
      editErr.value = e.status ? e.message || 'Ошибка сохранения' : 'Сеть'
      logError('schedule', 'linksToSettings:fail', { error: e.message })
    }
  }

  async function applyLinksFromConfig() {
    editErr.value = ''
    const cfg = singleConfig()
    if (!cfg) return
    try {
      const detail = await loadTutorConfiguration(cfg.config_id)
      editForm.lesson_links = (detail.default_links || []).map((l) => ({ alias: l.alias || '', url: l.url || '' }))
    } catch (e) {
      editErr.value = e.status ? e.message || 'Ошибка загрузки' : 'Сеть'
      logError('schedule', 'linksFromConfig:fail', { error: e.message })
    }
  }

  async function applyLinksToConfig() {
    editErr.value = ''
    editMsg.value = ''
    const cfg = singleConfig()
    if (!cfg) return
    try {
      await updateTutorConfiguration(cfg.config_id, { default_links: cleanLinks(editForm.lesson_links) })
      editMsg.value = 'Сохранено в конфигурацию'
      logInfo('schedule', 'linksToConfig:ok', { id: cfg.config_id })
      setTimeout(() => { if (editMsg.value === 'Сохранено в конфигурацию') editMsg.value = '' }, 3000)
    } catch (e) {
      editErr.value = e.status ? e.message || 'Ошибка сохранения' : 'Сеть'
      logError('schedule', 'linksToConfig:fail', { error: e.message })
    }
  }

  // --- Редактирование ---
  async function startEdit(l) {
    editingId.value = l.lesson_id
    editForm.start_time = l.start_time.replace(' ', 'T').slice(0, 16)
    editForm.end_time = l.end_time.replace(' ', 'T').slice(0, 16)
    editForm.is_group = l.is_group
    editForm.status = l.status || 'SCHEDULED'
    editForm.lesson_links = (l.lesson_links || []).map((x) => ({ alias: x.alias || '', url: x.url || '' }))
    editErrors.start_time = ''
    editErrors.end_time = ''
    editMsg.value = ''
    editErr.value = ''
    addParticipantErr.value = ''
    editDirty.value = false
    syncEditRows(l.lesson_id)
    await loadParticipants(l.lesson_id)
    if (!editDirty.value) syncEditRows(l.lesson_id)
  }

  function cancelEdit() {
    editingId.value = null
    editMsg.value = ''
    editErr.value = ''
    addParticipantErr.value = ''
    editOriginal.value = []
    editRows.value = []
    editDirty.value = false
  }

  function validateEdit() {
    editErrors.start_time = ''
    editErrors.end_time = ''
    let ok = true
    if (!editForm.start_time) {
      editErrors.start_time = 'Обязательное поле'
      ok = false
    }
    if (!editForm.end_time) {
      editErrors.end_time = 'Обязательное поле'
      ok = false
    }
    if (editForm.start_time && editForm.end_time && editForm.start_time >= editForm.end_time) {
      editErrors.end_time = 'Конец должен быть позже начала'
      ok = false
    }
    return ok
  }

  async function handleUpdate(l) {
    editMsg.value = ''
    editErr.value = ''
    addParticipantErr.value = ''
    if (!validateEdit()) return
    const linksErr = validateLinks()
    if (linksErr) {
      editErr.value = linksErr
      return
    }
    saving.value = true
    try {
      const orig = new Set(editOriginal.value)
      const curr = new Set(editRows.value.filter((r) => r.student_user_id).map((r) => r.student_user_id))
      const toAdd = [...curr].filter((id) => !orig.has(id))
      const toRemove = [...orig].filter((id) => !curr.has(id))
      let failed = []
      try {
        const result = await updateLessonWithParticipants(l.lesson_id, {
          timePatch: {
            start_time: editForm.start_time,
            end_time: editForm.end_time,
            is_group: editForm.is_group,
            lesson_links: cleanLinks(editForm.lesson_links),
            status: editForm.status !== l.status ? editForm.status : null,
          },
          originalIds: [...orig],
          currentIds: [...curr],
        })
        failed = result.failed
      } catch (e) {
        if (e.status) {
          editErr.value = e.payload?.error?.message || 'Ошибка'
          logError('schedule', 'update:fail', { status: e.status, error: e.payload?.error })
          return
        }
        throw e
      }
      const failures = failed.map((f) => {
        const name = studentName(f.uid)
        if (f.network) return `${name}: сеть`
        return `${name}: ${f.payload?.error?.message || (f.op === 'add' ? 'не добавлен' : 'не удалён')}`
      })

      await loadParticipants(l.lesson_id)
      syncEditRows(l.lesson_id)
      editDirty.value = false

      if (failures.length) {
        addParticipantErr.value = failures.join('; ')
        logError('schedule', 'update:participantsFail', { lesson_id: l.lesson_id, failures })
      } else {
        editMsg.value = 'Сохранено'
        logInfo('schedule', 'update:ok', {
          lesson_id: l.lesson_id,
          added: toAdd.length,
          removed: toRemove.length,
        })
        setTimeout(() => {
          editMsg.value = ''
          editingId.value = null
        }, 1000)
      }
    } catch (e) {
      editErr.value = 'Сеть'
      logError('schedule', 'update:networkError', { error: e.message })
    } finally {
      saving.value = false
    }
  }

  async function handleDelete(l) {
    saving.value = true
    try {
      await deleteLesson(l.lesson_id)
      const newSet = new Set(selectedIds.value)
      newSet.delete(l.lesson_id)
      selectedIds.value = newSet
      if (editingId.value === l.lesson_id) editingId.value = null
      logInfo('schedule', 'delete:ok', { lesson_id: l.lesson_id })
    } catch (e) {
      if (e.status) {
        logError('schedule', 'delete:fail', { status: e.status, error: e.payload?.error })
      } else {
        logError('schedule', 'delete:networkError', { error: e.message })
      }
    } finally {
      saving.value = false
    }
  }

  onMounted(async () => {
    logInfo('schedule', 'mounted:loading')
    try {
      const calls =
        authStore.role === 'student'
          ? [loadScheduleLessons(), loadStudentTutors(), loadStudentScheduleSettings()]
          : [loadScheduleLessons(), loadTutorStudents(), loadScheduleSettings()]
      const results = await Promise.allSettled(calls)
      const netFail = results.find((r) => r.status === 'rejected' && !r.reason.status)
      if (netFail) throw netFail.reason
      if (results[0].status === 'fulfilled') {
        logInfo('schedule', 'mounted:lessonsLoaded', { count: lessons.value.length })
      }
      if (authStore.role === 'tutor') loadBackgroundBookings()
      // Формы не переживают навигацию, а store — да: при входе оставляем
      // только окна репетиторов из живых форм (на монте их нет — чистка).
      pruneStudentWindows(pickedTutorIds.value)
    } catch (e) {
      logError('schedule', 'mounted:error', { error: e.message })
    } finally {
      loading.value = false
    }
  })

  onUnmounted(() => {
    // Уход со страницы гасит чужую подсветку полностью.
    clearStudentWindows()
  })

  return {
    lessons,
    students,
    tutors,
    tutorColors,
    resolvedTutorColors,
    weekRange,
    pickedTutorIds,
    outlinedWeekdays,
    participantsMap,
    dimBookings,
    freeWindows,
    selectedIds,
    loading,
    saving,
    editingId,
    editForm,
    editErrors,
    editMsg,
    editErr,
    participantsLoading,
    editRows,
    addParticipantErr,
    createSlots,
    visibleHours,
    dynamicGridH,
    weekDays,
    previewBlocks,
    prevWeek,
    nextWeek,
    goToday,
    fetchWeekWindows,
    ensureTutorColor,
    setTutorColor,
    clearSelection,
    toggleSelect,
    loadParticipants,
    addEditRow,
    removeEditRow,
    singlePick,
    addEditLink,
    removeEditLink,
    applyLinksFromConfig,
    applyLinksToConfig,
    applyLinksFromSettings,
    applyLinksToSettings,
    startEdit,
    cancelEdit,
    handleUpdate,
    handleDelete,
    clearCreateForm,
  }
}
