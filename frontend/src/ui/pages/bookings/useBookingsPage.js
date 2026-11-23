// UI-логика страницы броней: выбор, редактирование, пикер учеников,
// предзаполнение по клику, монтирование. Слоты создания живут здесь
// (модалка и префилл делят их с редактированием), содержимое слотов
// правит BookingCreator вложенными мутациями.
import { ref, reactive, computed, onMounted } from 'vue'
import {
  loadBookings,
  updateBooking,
  deleteBooking,
  loadTutorStudents,
} from '../../../logic/actions/index.js'
import { logInfo, logError, logState } from '../../../logic/logger/index.js'
import { useBookingsStore, useRosterStore } from '../../../logic/store/index.js'
import { ruleRequiresTargets } from '../../../logic/constants/index.js'
import { toMin, hasOverlap } from '../../../logic/utils/index.js'

export function useBookingsPage() {
  const bookingsStore = useBookingsStore()

  const bookings = computed(() => bookingsStore.bookings)
  const students = computed(() => useRosterStore().students)

  // Черновики из форм создания — на сетку (аналог превью в расписании).
  // Только корректные интервалы; невалидные подсветит валидация сабмита.
  const previewBookings = computed(() =>
    createSlots.value
      .filter((s) => s.start_time && s.end_time && toMin(s.start_time) < toMin(s.end_time))
      .map((s, i) => ({
        id: `pv-${i}`,
        weekday: s.weekday,
        start_time: s.start_time,
        end_time: s.end_time,
      })),
  )

  const loading = ref(true)
  const saving = ref(false)
  const selected = ref(null)
  const editing = ref(false)

  const createSlots = ref([])

  const editForm = reactive({ weekday: '', start_time: '', end_time: '', access_rule: 'EVERYONE', access_targets: [] })
  const editErrors = reactive({ overlap: '' })
  const editMsg = ref('')
  const editErr = ref('')
  const deleteErr = ref('')
  const updateMsg = ref('')

  const studentPicker = reactive({ show: false, slotIndex: null, mode: '' })

  function selectBooking(b) {
    selected.value = b
    editing.value = false
    deleteErr.value = ''
    updateMsg.value = ''
    editErrors.overlap = ''
    editMsg.value = ''
    editErr.value = ''
    logState('bookings', 'selectBooking', {
      id: b.id,
      weekday: b.weekday,
      time: `${b.start_time}–${b.end_time}`,
      rule: b.access_rule,
    })
  }

  function startEdit() {
    if (!selected.value) return
    editing.value = true
    editForm.weekday = selected.value.weekday
    editForm.start_time = selected.value.start_time
    editForm.end_time = selected.value.end_time
    editForm.access_rule = selected.value.access_rule
    editForm.access_targets = [...(selected.value.access_targets || [])]
    editErr.value = ''
    editMsg.value = ''
    editErrors.overlap = ''
    logState('bookings', 'startEdit', { id: selected.value.id })
  }

  function cancelEdit() {
    editing.value = false
    editErrors.overlap = ''
    editMsg.value = ''
    editErr.value = ''
    logState('bookings', 'cancelEdit')
  }

  function openStudentPicker(slotIndex, mode) {
    studentPicker.slotIndex = slotIndex
    studentPicker.mode = mode
    studentPicker.show = true
  }

  function openEditPicker() {
    openStudentPicker(null, 'edit')
  }

  function openCreatePicker(slotIndex) {
    openStudentPicker(slotIndex, 'create')
  }

  function removeEditTarget(studentId) {
    removeTarget(null, 'edit', studentId)
  }

  function closeStudentPicker() {
    studentPicker.show = false
    studentPicker.slotIndex = null
    studentPicker.mode = ''
  }

  function pickStudent(studentId) {
    if (studentPicker.mode === 'edit') {
      editForm.access_targets.push(studentId)
    } else {
      createSlots.value[studentPicker.slotIndex].access_targets.push(studentId)
    }
    closeStudentPicker()
  }

  function removeTarget(slotIndex, mode, studentId) {
    if (mode === 'edit') {
      editForm.access_targets = editForm.access_targets.filter((id) => id !== studentId)
    } else {
      const targets = createSlots.value[slotIndex].access_targets
      const idx = targets.indexOf(studentId)
      if (idx !== -1) targets.splice(idx, 1)
    }
  }

  function availableStudents() {
    const targets =
      studentPicker.mode === 'edit'
        ? editForm.access_targets
        : createSlots.value[studentPicker.slotIndex]?.access_targets || []
    return students.value.filter((s) => !targets.includes(s.student_id))
  }

  function prefillCreateSlot({ day, startTime, endTime }) {
    selected.value = null
    editing.value = false
    createSlots.value.splice(0, createSlots.value.length, {
      weekday: day,
      start_time: startTime,
      end_time: endTime,
      access_rule: 'EVERYONE',
      access_targets: [],
    })
  }

  function studentName(sid) {
    const s = students.value.find((x) => x.student_id === sid)
    return s ? s.full_name : `#${sid}`
  }

  function validateEdit() {
    editErrors.overlap = ''
    editMsg.value = ''
    editErr.value = ''
    let ok = true
    const slot = editForm
    let err = ''
    if (slot.start_time && slot.end_time && toMin(slot.start_time) >= toMin(slot.end_time)) {
      err = 'Конец должен быть позже начала'
    } else if (
      slot.start_time &&
      slot.end_time &&
      hasOverlap(bookings.value, slot.weekday, slot.start_time, slot.end_time, selected.value?.id)
    ) {
      err = 'Пересечение'
    } else if (ruleRequiresTargets(slot.access_rule) && !slot.access_targets?.length) {
      err = 'Добавьте учеников'
    }
    if (err) {
      editErrors.overlap = err
      ok = false
    }
    return ok
  }

  async function handleUpdate() {
    logInfo('bookings', 'update:submit', { id: selected.value?.id, form: { ...editForm } })
    if (!validateEdit() || !selected.value) {
      logInfo('bookings', 'update:validationFailed', { errors: { ...editErrors } })
      return
    }
    saving.value = true
    try {
      const mapped = await updateBooking(selected.value.id, { ...editForm })
      selected.value = mapped
      editing.value = false
      updateMsg.value = 'Сохранено'
      logInfo('bookings', 'update:ok', { result: mapped })
      setTimeout(() => (updateMsg.value = ''), 3000)
    } catch (e) {
      if (e.status) {
        editErr.value = e.message || 'Ошибка'
        logError('bookings', 'update:fail', { status: e.status, error: e.payload?.error })
      } else {
        editErr.value = 'Сеть'
        logError('bookings', 'update:networkError', { error: e.message })
      }
    } finally {
      saving.value = false
    }
  }

  async function handleDelete() {
    if (!selected.value) return
    logInfo('bookings', 'delete:confirm', { id: selected.value.id })
    saving.value = true
    try {
      await deleteBooking(selected.value.id)
      selected.value = null
      editing.value = false
      logInfo('bookings', 'delete:ok')
    } catch (e) {
      if (e.status) {
        deleteErr.value = e.message || 'Ошибка'
        logError('bookings', 'delete:fail', { status: e.status, error: e.payload?.error })
      } else {
        deleteErr.value = 'Сеть'
        logError('bookings', 'delete:networkError', { error: e.message })
      }
    } finally {
      saving.value = false
    }
  }

  onMounted(async () => {
    logInfo('bookings', 'mounted:loading')
    try {
      try {
        await loadBookings()
        logInfo('bookings', 'mounted:bookingsLoaded', { count: bookings.value.length })
      } catch (e) {
        if (!e.status) throw e
      }
      try {
        await loadTutorStudents()
        logInfo('bookings', 'mounted:studentsLoaded', { count: students.value.length })
      } catch (e) {
        if (!e.status) throw e
      }
    } catch (e) {
      logError('bookings', 'mounted:error', { error: e.message })
    } finally {
      loading.value = false
    }
  })

  return {
    bookings,
    students,
    previewBookings,
    loading,
    saving,
    selected,
    editing,
    createSlots,
    editForm,
    editErrors,
    editMsg,
    editErr,
    deleteErr,
    updateMsg,
    studentPicker,
    selectBooking,
    startEdit,
    cancelEdit,
    openStudentPicker,
    openEditPicker,
    openCreatePicker,
    removeEditTarget,
    closeStudentPicker,
    pickStudent,
    removeTarget,
    availableStudents,
    prefillCreateSlot,
    studentName,
    handleUpdate,
    handleDelete,
  }
}
