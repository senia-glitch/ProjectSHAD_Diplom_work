// Состояние страницы оплат: период, ученик, реестр строк, отметка оплаты.
import { ref, computed, watch, onMounted } from 'vue'
import { loadLessonDetails, setParticipantPaid, loadTutorStudents } from '../../../logic/actions/index.js'
import { useRosterStore } from '../../../logic/store/index.js'
import { buildPaymentRows, filterPaymentRows, summarizePayments } from '../../../logic/utils/index.js'
import { logError } from '../../../logic/logger/index.js'

// ISO-дата из локальных полей: toISOString() сдвигает локальную полночь
// на день назад в таймзонах восточнее UTC — дефолтный месяц оплат
// начинался 30-м числом предыдущего месяца.
function isoLocal(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function monthRange() {
  const now = new Date()
  const from = new Date(now.getFullYear(), now.getMonth(), 1)
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return { from: isoLocal(from), to: isoLocal(to) }
}

// Состояние общее для страницы «Оплаты», вкладки статистики и её панели фильтров:
// фильтр, выбранный в панели, сразу меняет таблицу.
const range = monthRange()
const dateFrom = ref(range.from)
const dateTo = ref(range.to)
const studentId = ref('')
const paidFilter = ref('all')
const lessons = ref([])
const loading = ref(false)
const error = ref('')
const togglingId = ref('')

export function usePaymentsPage({ root = false } = {}) {
  const rosterStore = useRosterStore()

  const students = computed(() => rosterStore.students || [])
  const rows = computed(() => filterPaymentRows(buildPaymentRows(lessons.value), paidFilter.value))
  const summary = computed(() => summarizePayments(rows.value))

  async function reload() {
    loading.value = true
    error.value = ''
    try {
      lessons.value = await loadLessonDetails({
        dateFrom: dateFrom.value,
        dateTo: dateTo.value,
        studentIds: studentId.value ? [Number(studentId.value)] : undefined,
      })
    } catch (e) {
      error.value = e.payload?.error?.message || e.message || 'Не удалось загрузить оплаты'
      logError('payments', 'reload:error', { error: e.message })
    } finally {
      loading.value = false
    }
  }

  async function togglePaid(row) {
    togglingId.value = row.lesson_id + ':' + row.student_id
    try {
      await setParticipantPaid(row.lesson_id, row.student_user_id, !row.paid)
      await reload()
    } catch (e) {
      error.value = e.message || 'Не удалось изменить оплату'
      logError('payments', 'toggle:error', { error: e.message })
    } finally {
      togglingId.value = ''
    }
  }

  // Владелец данных (страница или вкладка) загружает их при каждом открытии и при смене фильтров.
  if (root) {
    watch([dateFrom, dateTo, studentId], reload)
    onMounted(async () => {
      try {
        await loadTutorStudents()
      } catch (e) {
        logError('payments', 'roster:error', { error: e.message })
      }
      await reload()
    })
  }

  return {
    dateFrom, dateTo, studentId, paidFilter,
    students, rows, summary, loading, error, togglingId,
    togglePaid, reload,
  }
}
