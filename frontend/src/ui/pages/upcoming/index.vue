<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="upcoming-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Ближайшие уроки</h1>
          <router-link to="/schedule" class="btn btn--gry btn--sm">К расписанию</router-link>
        </div>
        <p class="page-desc">
          Уроки на неделю вперёд в вашем часовом поясе
          <template v-if="pendingCount">· <strong>{{ pendingCount }}</strong> {{ role === 'tutor' ? 'ждут вашего подтверждения' : 'ждут подтверждения репетитора' }}</template>
        </p>
      </div>

      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="error" class="fmsg fmsg--err">{{ error }}</div>

      <template v-else>
        <div v-if="!days.length" class="empty-card">
          <p>На ближайшую неделю уроков нет.</p>
          <router-link to="/schedule" class="btn btn--pri btn--sm">{{ role === 'student' ? 'Записаться на урок' : 'Открыть расписание' }}</router-link>
        </div>

        <section v-for="day in days" :key="day.date" class="day-block" :aria-labelledby="`day-${day.date}`">
          <h2 :id="`day-${day.date}`" class="day-title">{{ day.label }}</h2>
          <article v-for="l in day.lessons" :key="l.lesson_id" class="lesson-card" :class="`lesson-card--${l.status.toLowerCase()}`">
            <div class="lesson-main">
              <div class="lesson-time">{{ lessonTimeLabel(l.start_time, l.end_time) }}</div>
              <div class="lesson-info">
                <div class="lesson-who">{{ whoOf(l) }}</div>
                <div class="lesson-meta">
                  <span class="status-chip" :style="{ color: lessonStatusColor(l.status) }">{{ lessonStatusLabel(l.status) }}</span>
                  <span>· {{ l.is_group ? 'Групповой' : 'Индивидуальный' }}</span>
                </div>
              </div>
            </div>
            <LessonNotes :note="l.status_note" :absence="l.absence" />
            <div v-if="safeLinks(l).length" class="lesson-links">
              <a v-for="link in safeLinks(l)" :key="link.safe" :href="link.safe" target="_blank" rel="noopener noreferrer" class="link-btn">
                <UiIcon name="open" /> {{ link.alias }}
              </a>
            </div>
            <div class="lesson-actions">
              <router-link :to="`/lessons/${l.lesson_id}`" class="btn btn--gry btn--sm">Открыть урок</router-link>
              <template v-if="role === 'tutor' && l.status === 'PENDING'">
                <button type="button" class="btn btn--pri btn--sm" :disabled="busy" @click="confirm(l)">Подтвердить</button>
                <button type="button" class="btn btn--dan btn--sm" :disabled="busy" @click="openDecision('reject', l)">Отклонить</button>
              </template>
              <button
                v-if="role === 'student' && (l.status === 'SCHEDULED' || l.status === 'PENDING')"
                type="button"
                class="btn btn--dan btn--sm"
                :disabled="busy"
                @click="openDecision('cancel', l)"
              >{{ l.status === 'PENDING' ? 'Отозвать заявку' : 'Отменить' }}</button>
            </div>
          </article>
        </section>

        <section v-if="history.length" class="day-block history-block" aria-labelledby="history-title">
          <h2 id="history-title" class="day-title">История отмен</h2>
          <p class="page-desc">Отменённые, отклонённые и закрытые системой уроки за последние 30 дней: кто, когда и почему.</p>
          <article v-for="l in history" :key="l.lesson_id" class="lesson-card lesson-card--history">
            <div class="lesson-main">
              <div class="lesson-time">{{ formatMoment(l.start_time) }}</div>
              <div class="lesson-info">
                <div class="lesson-meta">
                  <span class="status-chip" :style="{ color: lessonStatusColor(l.status) }">{{ lessonStatusLabel(l.status) }}</span>
                  <router-link :to="`/lessons/${l.lesson_id}`" class="history-link">Подробнее</router-link>
                </div>
              </div>
            </div>
            <LessonNotes :note="l.status_note" />
          </article>
        </section>
      </template>
    </div>

    <ReasonDialog
      ref="decisionDialog"
      :title="decisionKind === 'reject' ? 'Отклонить заявку?' : (decisionLesson?.status === 'PENDING' ? 'Отозвать заявку?' : 'Отменить урок?')"
      :text="decisionKind === 'reject' ? 'Ученик получит уведомление с причиной.' : 'Репетитор получит уведомление. Отмена попадёт в историю урока.'"
      :confirm-label="decisionKind === 'reject' ? 'Отклонить' : (decisionLesson?.status === 'PENDING' ? 'Отозвать' : 'Отменить урок')"
      :busy="busy"
      :error="decisionError"
      @confirm="onDecision"
    />
  </MainLayout>
</template>

<script setup>
// Раздел «Ближайшие уроки» (группа «Занятия»): неделя вперёд, быстрые действия, история отмен.
import { ref, computed, onMounted } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { LessonNotes, ReasonDialog, UiIcon } from '../../components/index.js'
import { useUser, useLogout } from '../../composables/index.js'
import {
  loadUpcomingLessons,
  loadTutorStudents,
  loadStudentTutors,
  cancelLessonAsStudent,
  confirmLessonRequest,
  rejectLessonRequest,
} from '../../../logic/actions/index.js'
import { useRosterStore } from '../../../logic/store/index.js'
import {
  groupUpcoming,
  userNowIso,
  lessonTimeLabel,
  lessonStatusLabel,
  lessonStatusColor,
  lessonSafeLinks,
  formatMoment,
  tutorNameOf,
} from '../../../logic/utils/index.js'
import { logError } from '../../../logic/logger/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const roster = useRosterStore()

const lessons = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)

const grouped = computed(() => groupUpcoming(lessons.value, userNowIso()))
const days = computed(() => grouped.value.days)
const history = computed(() => grouped.value.history)
const pendingCount = computed(() => grouped.value.pendingCount)

function whoOf(lesson) {
  if (role.value === 'student') return tutorNameOf(lesson, roster.tutors)
  const names = (lesson.participants || [])
    .map((p) => roster.students.find((s) => s.user_id === p.student_user_id)?.full_name)
    .filter(Boolean)
  return names.length ? names.join(', ') : 'Без учеников'
}

function safeLinks(lesson) {
  return lessonSafeLinks(lesson.lesson_links)
}

async function reload() {
  error.value = ''
  try {
    lessons.value = await loadUpcomingLessons()
  } catch (e) {
    error.value = e.status ? (e.message || 'Не удалось загрузить уроки') : 'Ошибка сети'
    logError('upcoming', 'load:error', { error: e.message })
  } finally {
    loading.value = false
  }
}

// Решения: отмена учеником, отклонение/подтверждение заявки репетитором.
const decisionDialog = ref(null)
const decisionKind = ref('cancel')
const decisionLesson = ref(null)
const decisionError = ref('')

function openDecision(kind, lesson) {
  decisionKind.value = kind
  decisionLesson.value = lesson
  decisionError.value = ''
  decisionDialog.value?.open()
}

async function onDecision(reason) {
  busy.value = true
  decisionError.value = ''
  try {
    const action = decisionKind.value === 'reject' ? rejectLessonRequest : cancelLessonAsStudent
    await action(decisionLesson.value.lesson_id, reason)
    decisionDialog.value?.close()
    await reload()
  } catch (e) {
    decisionError.value = e.message || 'Не удалось сохранить'
  } finally {
    busy.value = false
  }
}

async function confirm(lesson) {
  busy.value = true
  try {
    await confirmLessonRequest(lesson.lesson_id)
    await reload()
  } catch (e) {
    error.value = e.message || 'Не удалось подтвердить заявку'
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    if (role.value === 'tutor') await loadTutorStudents()
    else await loadStudentTutors()
  } catch (e) {
    logError('upcoming', 'roster:error', { error: e.message })
  }
  await reload()
})
</script>

<style scoped>
.upcoming-page { display: flex; flex-direction: column; gap: 8px; }
.page-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.empty-card {
  display: grid; gap: 12px; justify-items: start; padding: 20px;
  border: 1px dashed var(--line, var(--color-gray-300)); border-radius: var(--r-md, 12px);
}
.empty-card p { margin: 0; color: var(--muted, var(--color-gray-600)); }
.day-block { display: grid; gap: 10px; margin-top: 16px; }
.day-title { margin: 0; font-size: 16px; text-transform: none; }
.lesson-card {
  display: grid; gap: 10px; padding: 14px 16px;
  border: 1px solid var(--line, var(--color-gray-300)); border-radius: var(--r-md, 12px);
  background: var(--surface, transparent);
}
.lesson-card--pending { border-style: dashed; border-color: var(--rule-only-border, #d4a72c); }
.lesson-card--ongoing { border-color: var(--color-success); }
.lesson-card--history { opacity: .85; }
.lesson-main { display: flex; gap: 16px; align-items: baseline; flex-wrap: wrap; }
.lesson-time { font-size: 18px; font-weight: 600; font-variant-numeric: tabular-nums; min-width: 120px; }
.lesson-info { display: grid; gap: 2px; min-width: 0; }
.lesson-who { font-weight: 500; overflow-wrap: anywhere; }
.lesson-meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; color: var(--muted, var(--color-gray-600)); font-size: 13px; }
.status-chip { font-weight: 600; }
.lesson-links { display: flex; gap: 8px; flex-wrap: wrap; }
.link-btn { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; }
.link-btn :deep(svg) { width: 14px; height: 14px; }
.lesson-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.history-link { font-size: 13px; }
@media (max-width: 720px) {
  .lesson-time { min-width: 0; font-size: 16px; }
}
</style>
