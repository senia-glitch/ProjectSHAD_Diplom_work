<template>
  <div class="pp activity">
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-else-if="loading" class="skeleton" aria-hidden="true"></div>

    <!-- Уроки: ближайшие сверху, затем прошедшие -->
    <template v-else-if="tab === 'lessons'">
      <p class="muted small period">Последние 3 месяца и ближайшие 2.</p>
      <p v-if="!lessonRows.length" class="muted">Уроков за период нет.</p>
      <template v-for="group in lessonGroups" :key="group.title">
        <h4 v-if="group.rows.length" class="group-title">{{ group.title }}</h4>
        <ul v-if="group.rows.length" class="rows">
          <li v-for="r in group.rows" :key="r.lesson_id">
            <router-link :to="`/lessons/${r.lesson_id}`" class="row-link">
              <span class="when">{{ formatDay(r.date) }} · {{ r.start }}–{{ r.end }}</span>
              <span class="pill" :class="statusPill(r.status)">{{ lessonStatusLabel(r.status) }}</span>
              <span class="grow"></span>
              <span class="muted small">{{ formatMoney(r.amount) }}</span>
            </router-link>
          </li>
        </ul>
      </template>
    </template>

    <!-- Оплаты ученика: сводка и отметка оплаты -->
    <template v-else-if="tab === 'payments'">
      <p class="muted small period">Последние 3 месяца и ближайшие 2.</p>
      <div class="totals">
        <div class="total"><span class="muted small">Оплачено</span><strong class="ok-text">{{ formatMoney(summary.collected) }}</strong></div>
        <div class="total"><span class="muted small">Не оплачено</span><strong :class="{ 'error-text': summary.debt }">{{ formatMoney(summary.debt) }}</strong></div>
      </div>
      <p v-if="!paymentRows.length" class="muted">Записей за период нет.</p>
      <ul v-else class="rows">
        <li v-for="r in paymentRows" :key="r.lesson_id" class="pay-row">
          <router-link :to="`/lessons/${r.lesson_id}`" class="when">{{ formatDay(r.date) }} · {{ r.start }}</router-link>
          <span class="grow"></span>
          <span>{{ formatMoney(r.amount) }}</span>
          <button type="button" class="pay" :class="{ on: r.paid }" :aria-pressed="r.paid" :disabled="toggling === r.lesson_id" @click="togglePaid(r)">
            {{ r.paid ? 'Оплачено' : 'Не оплачено' }}
          </button>
        </li>
      </ul>
    </template>

    <!-- Тесты: результаты ученика по моим тестам -->
    <template v-else-if="tab === 'tests'">
      <p v-if="!tests.length" class="muted">Ученик ещё не проходил ваши тесты. Откройте доступ к тесту в разделе «Тесты».</p>
      <ul v-else class="rows">
        <li v-for="t in tests" :key="t.id">
          <router-link :to="`/testing/results/${t.id}`" class="row-link">
            <span class="grow"><strong>{{ t.test_title }}</strong><span class="muted small"> · {{ formatDay(String(t.submitted_at).slice(0, 10)) }}</span></span>
            <span>{{ t.score }} / {{ t.max_score }}</span>
            <span v-if="t.teacher_grade" class="pill pill-green">{{ t.teacher_grade }}</span>
            <span v-else class="pill pill-amber">не проверен</span>
          </router-link>
        </li>
      </ul>
    </template>
  </div>
</template>

<script setup>
// Вкладки карточки ученика: уроки, оплаты и результаты тестов одного ученика.
import { computed, ref, watch } from 'vue'
import { loadLessonDetails, loadStudentTestResults, setParticipantPaid } from '../../../logic/actions/index.js'
import { buildPaymentRows, formatMoney, lessonStatusLabel, summarizePayments, userNowIso } from '../../../logic/utils/index.js'
import { toast } from '../../legacy/testing/kit.js'

const props = defineProps({
  studentId: { type: Number, required: true },
  tab: { type: String, required: true },
})

const lessons = ref([])
const tests = ref([])
const loading = ref(false)
const error = ref('')
const toggling = ref(null)
const loaded = new Set()

function shiftDays(days) {
  const d = new Date(userNowIso().slice(0, 10) + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const today = () => userNowIso().slice(0, 10)
const lessonRows = computed(() => lessons.value.map((l) => ({
  ...l, amount: (l.students || []).reduce((sum, s) => sum + (s.amount || 0), 0),
})))
const lessonGroups = computed(() => {
  const now = today()
  const upcoming = lessonRows.value.filter((r) => r.date >= now).sort((a, b) => (a.date + a.start).localeCompare(b.date + b.start))
  const past = lessonRows.value.filter((r) => r.date < now).sort((a, b) => (b.date + b.start).localeCompare(a.date + a.start))
  return [{ title: 'Ближайшие', rows: upcoming }, { title: 'Прошедшие', rows: past }]
})
const paymentRows = computed(() => buildPaymentRows(lessons.value))
const summary = computed(() => summarizePayments(paymentRows.value))

const formatDay = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '')
  return m ? `${m[3]}.${m[2]}.${m[1]}` : iso
}
const statusPill = (s) => ({ FINISHED: 'pill-green', SCHEDULED: 'pill-blue', ONGOING: 'pill-green', PENDING: 'pill-amber' }[s] || 'pill-gray')

async function load(force = false) {
  const kind = props.tab === 'tests' ? 'tests' : 'lessons'
  if (!force && loaded.has(kind)) return
  loading.value = true
  error.value = ''
  try {
    if (kind === 'tests') tests.value = await loadStudentTestResults(props.studentId)
    else lessons.value = await loadLessonDetails({ dateFrom: shiftDays(-90), dateTo: shiftDays(60), studentIds: [props.studentId] })
    loaded.add(kind)
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить данные'
  } finally {
    loading.value = false
  }
}

async function togglePaid(row) {
  toggling.value = row.lesson_id
  try {
    await setParticipantPaid(row.lesson_id, row.student_user_id, !row.paid)
    await load(true)
  } catch (e) {
    toast(e.message || 'Не удалось изменить оплату', 'error')
  } finally {
    toggling.value = null
  }
}

watch(() => props.studentId, () => { loaded.clear(); lessons.value = []; tests.value = []; load() })
watch(() => props.tab, () => load(), { immediate: true })
</script>

<style scoped>
.activity { display: grid; gap: 10px; }
.period { margin: 0; }
.group-title { margin: 8px 0 0; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.rows { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.row-link, .pay-row { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 10px; color: var(--text); }
.row-link:hover { background: var(--surface-2); text-decoration: none; }
.pay-row .when { color: var(--text); }
.when { white-space: nowrap; }
.totals { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.total { display: grid; gap: 2px; padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px; }
.total strong { font-size: 18px; }
.pay { height: 28px; padding: 0 12px; border-radius: 999px; border: 1px solid var(--line-strong); background: var(--surface-2); color: var(--muted); font: 500 12.5px var(--sans); cursor: pointer; white-space: nowrap; }
.pay.on { background: color-mix(in srgb, var(--ok) 16%, transparent); border-color: var(--ok); color: var(--ok); }
.pay:disabled { opacity: .6; }
</style>
