<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp lesson-page">
      <div class="toolbar">
        <div>
          <router-link class="back" to="/schedule">← Расписание</router-link>
          <h1>{{ lesson ? lessonDateLabel(lesson.start_time) : 'Урок' }}</h1>
          <p v-if="lesson" class="lead">
            {{ lessonTimeLabel(lesson.start_time, lesson.end_time) }} · {{ lesson.is_group ? 'групповой' : 'индивидуальный' }}
            <template v-if="!isTutor && tutorName"> · {{ tutorName }}</template>
          </p>
        </div>
        <div v-if="lesson" class="row">
          <span class="pill" :class="statusPill">{{ statusLabel(lesson.status) }}</span>
        </div>
      </div>

      <div v-if="loading" class="skeleton tall" aria-hidden="true"></div>
      <div v-else-if="error" class="notice error" role="alert">{{ error }} <router-link to="/schedule">К расписанию</router-link></div>

      <template v-else-if="lesson">
        <!-- ===== Вход на занятие ===== -->
        <section class="join" :class="`join--${phase.kind}`" aria-labelledby="join-title">
          <div class="join-state">
            <span class="join-icon" aria-hidden="true"><UiIcon :name="phaseIcon" /></span>
            <div>
              <h2 id="join-title" class="join-title">{{ phaseTitle }}</h2>
              <p v-if="phaseHint" class="join-hint">{{ phaseHint }}</p>
            </div>
          </div>

          <div v-if="showLinks" class="join-actions">
            <!-- Доска урока: у каждого урока своя, без кода; необязательна, но всегда под рукой -->
            <button type="button" class="btn board-btn" :class="joinable && !links.length ? 'primary big' : 'ghost'" :disabled="boardOpening" @click="openBoard">
              <UiIcon name="board" /> {{ boardOpening ? 'Открываем доску…' : 'Доска урока' }}
            </button>
            <template v-if="linksVisible">
              <template v-for="(l, i) in links" :key="l.safe + i">
                <router-link v-if="l.to" :to="l.to" class="btn" :class="i === 0 && joinable ? 'primary big' : 'ghost'">
                  <UiIcon name="board" /> {{ l.alias }}
                </router-link>
                <a v-else :href="l.safe" target="_blank" rel="noopener noreferrer" class="btn" :class="i === 0 && joinable ? 'primary big' : 'ghost'">
                  <UiIcon name="open" /> {{ l.alias }}
                </a>
              </template>
              <p v-if="!links.length" class="join-hint">
                {{ isTutor ? 'Ссылки на звонок нет — добавьте её в расписании или проводите урок на доске.' : 'Ссылки на звонок нет — урок может проходить на доске.' }}
              </p>
            </template>
            <p v-else class="join-hint">Ссылки на занятие появятся за {{ durationText(linksInMinutes) }} до начала.</p>
          </div>

          <!-- Решения по заявке и отметки урока -->
          <div v-if="isTutor && lesson.status === 'PENDING'" class="join-decide">
            <button type="button" class="btn primary" :disabled="busy" @click="confirmRequest">Подтвердить заявку</button>
            <button type="button" class="btn danger" :disabled="busy" @click="rejectDialog.open()">Отклонить</button>
            <span v-if="decisionError" class="error-text" role="alert">{{ decisionError }}</span>
          </div>
          <div v-else-if="isTutor && canMark" class="join-decide">
            <template v-if="phase.kind === 'live' || phase.kind === 'over'">
              <button type="button" class="btn primary" :disabled="busy" @click="markDialog('FINISHED')"><UiIcon name="check" /> Урок проведён</button>
              <button type="button" class="btn ghost" :disabled="busy" @click="markDialog('NO_SHOW')">Неявка</button>
            </template>
            <button type="button" class="btn ghost danger-text" :disabled="busy" @click="markDialog('CANCELLED')">Отменить урок</button>
          </div>
          <div v-else-if="!isTutor && lesson.can_cancel" class="join-decide">
            <button type="button" class="btn ghost danger-text" :disabled="busy" @click="cancelDialog.open()">
              {{ lesson.status === 'PENDING' ? 'Отозвать заявку' : 'Отменить урок' }}
            </button>
            <span v-if="lesson.cancel_deadline" class="muted small">Отменить можно до {{ formatMoment(lesson.cancel_deadline) }}</span>
          </div>
          <p v-else-if="!isTutor && lesson.cancel_deadline && isActiveStatus(lesson.status)" class="muted small join-decide">
            Срок отмены прошёл {{ formatMoment(lesson.cancel_deadline) }}: отменить урок может только репетитор.
          </p>
        </section>

        <LessonNotes class="notes" :note="lesson.status_note" :absence="lesson.absence" />

        <div class="lesson-grid" :class="{ 'lesson-grid--solo': !isTutor && !historyCount }">
          <div v-if="isTutor || historyCount" class="lesson-main">
            <!-- ===== Участники и оплаты (репетитор) ===== -->
            <section v-if="isTutor" class="panel">
              <div class="panel-head">
                <h3>Участники <small class="muted">{{ activeStudents }}</small></h3>
                <span class="muted small">Итого: <strong class="total">{{ formatMoney(lesson.total) }}</strong></span>
              </div>
              <p v-if="!lesson.students?.length" class="muted">На урок пока никто не записан.</p>
              <ul v-else class="people">
                <li v-for="s in lesson.students" :key="s.student_id" :class="{ cancelled: s.cancelled }">
                  <span class="avatar small" aria-hidden="true">{{ initials(s.student_name) }}</span>
                  <div class="grow">
                    <strong>{{ s.student_name }}</strong>
                    <div v-if="s.cancelled" class="small danger-text">
                      Запись отменена {{ s.cancelled_by === 'student' ? 'учеником' : s.cancelled_by === 'system' ? 'системой' : 'репетитором' }}<template v-if="s.cancelled_at">, {{ formatMoment(s.cancelled_at) }}</template><template v-if="s.cancel_reason">: {{ s.cancel_reason }}</template>
                    </div>
                    <div v-else class="small muted">{{ formatMoney(s.amount) }}</div>
                  </div>
                  <button
                    v-if="!s.cancelled"
                    type="button"
                    class="pay"
                    :class="{ on: s.paid }"
                    :aria-pressed="s.paid"
                    :disabled="busy"
                    @click="togglePaid(s)"
                  >{{ s.paid ? 'Оплачено' : 'Не оплачено' }}</button>
                  <button v-if="!s.cancelled" type="button" class="ibtn danger" data-tip="Убрать с урока" :aria-label="`Убрать ${s.student_name} с урока`" :disabled="busy" @click="removeParticipant(s)"><UiIcon name="trash" /></button>
                </li>
              </ul>
              <p v-if="canEditPeople && !roster.length" class="muted small add-part">Чтобы записывать учеников, свяжитесь с ними в разделе «Ученики».</p>
              <form v-else-if="canEditPeople" class="row add-part" @submit.prevent="addParticipant">
                <select v-model="newParticipant" :disabled="busy" aria-label="Ученик для записи на урок">
                  <option value="">Добавить ученика…</option>
                  <option v-for="s in roster" :key="s.user_id" :value="String(s.user_id)">{{ s.full_name || `Ученик #${s.user_id}` }}</option>
                </select>
                <button type="submit" class="btn" :disabled="busy || !newParticipant"><UiIcon name="plus" /> Добавить</button>
              </form>
            </section>

            <section v-if="isTutor && lesson.descriptions" class="panel">
              <h3>Описание</h3>
              <p class="pre">{{ lesson.descriptions }}</p>
            </section>

            <section v-if="historyCount" class="panel">
              <LessonNotes :history="lesson.status_history || []" show-history />
            </section>
          </div>

          <aside class="lesson-side">
            <!-- ===== Материалы урока ===== -->
            <section class="side-card">
              <h2>Материалы урока</h2>
              <template v-if="isTutor">
                <ul v-if="links.length" class="link-list">
                  <li v-for="(l, i) in links" :key="l.safe + i">
                    <UiIcon :name="l.boardId ? 'board' : 'open'" class="li-ico" />
                    <span class="grow">{{ l.alias }}</span>
                    <button type="button" class="ibtn danger" :aria-label="`Убрать ссылку ${l.alias}`" data-tip="Убрать" :disabled="busy" @click="removeLink(l)"><UiIcon name="trash" /></button>
                  </li>
                </ul>
                <p v-if="!links.length" class="muted small">Ссылок нет.</p>
              </template>
              <p class="muted small">У урока своя доска: репетитор и записанные ученики входят в неё без кода.</p>
              <router-link class="btn ghost" to="/boards"><UiIcon name="board" /> Свободные доски</router-link>
              <router-link class="btn ghost" :to="isTutor ? '/testing' : '/testing'"><UiIcon name="tests" /> {{ isTutor ? 'Тесты для учеников' : 'Мои тесты' }}</router-link>
              <router-link v-if="isTutor" class="btn ghost" to="/testing/new"><UiIcon name="plus" /> Новый тест</router-link>
            </section>

            <section v-if="isTutor" class="side-card">
              <h2>Урок</h2>
              <router-link class="btn ghost" to="/schedule"><UiIcon name="calendar" /> Изменить время и ссылки</router-link>
              <button type="button" class="btn ghost danger-text" :disabled="busy" @click="handleDelete"><UiIcon name="trash" /> Удалить урок</button>
            </section>
          </aside>
        </div>
      </template>
    </div>

    <ReasonDialog
      ref="cancelDialog"
      :title="lesson?.status === 'PENDING' ? 'Отозвать заявку?' : 'Отменить урок?'"
      text="Репетитор получит уведомление. Отмена попадёт в историю урока."
      :confirm-label="lesson?.status === 'PENDING' ? 'Отозвать' : 'Отменить урок'"
      :busy="busy"
      :error="decisionError"
      @confirm="onCancel"
    />
    <ReasonDialog
      ref="rejectDialog"
      title="Отклонить заявку?"
      text="Ученик получит уведомление с причиной."
      confirm-label="Отклонить"
      :busy="busy"
      :error="decisionError"
      @confirm="onReject"
    />
    <ReasonDialog
      ref="markRef"
      :title="markCopy.title"
      :text="markCopy.text"
      :confirm-label="markCopy.label"
      :danger="markStatusValue !== 'FINISHED'"
      :placeholder="markCopy.placeholder"
      :busy="busy"
      :error="decisionError"
      @confirm="onMark"
    />
  </MainLayout>
</template>

<script setup>
import { computed, ref } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { LessonNotes, ReasonDialog, UiIcon } from '../../components/index.js'
import { useUser, useLogout } from '../../composables/index.js'
import { useLessonPage } from './useLessonPage.js'
import { useRosterStore } from '../../../logic/store/index.js'
import {
  tutorNameOf, lessonDateLabel, lessonTimeLabel, formatMoment, lessonStatusLabel, durationText, formatMoney,
} from '../../../logic/utils/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const rosterStore = useRosterStore()
const {
  lesson, loading, error, busy, isTutor, roster, newParticipant, boardOpening,
  phase, links, linksVisible, linksInMinutes,
  togglePaid, addParticipant, removeParticipant, handleDelete, openBoard, removeLink,
  decisionError, cancelAsStudent, confirmRequest, rejectRequest, markStatus,
} = useLessonPage()

const cancelDialog = ref(null)
const rejectDialog = ref(null)
const markRef = ref(null)
const markStatusValue = ref('FINISHED')

const statusLabel = lessonStatusLabel
const tutorName = computed(() => tutorNameOf(lesson.value, rosterStore.tutors))
const initials = (name) => (name || '?').trim().slice(0, 1).toUpperCase() || '?'
const isActiveStatus = (status) => status === 'SCHEDULED' || status === 'PENDING'
const activeStudents = computed(() => (lesson.value?.students || []).filter((s) => !s.cancelled).length)
const historyCount = computed(() => (lesson.value?.status_history || []).length)
const canMark = computed(() => ['SCHEDULED', 'ONGOING'].includes(lesson.value?.status || 'SCHEDULED'))
const canEditPeople = computed(() => ['upcoming', 'soon', 'live'].includes(phase.value.kind))
// Вход имеет смысл до урока и во время него; у прошедшего и отменённого ссылки — справочно.
const joinable = computed(() => ['soon', 'live'].includes(phase.value.kind))
const showLinks = computed(() => phase.value.kind !== 'closed')

const statusPill = computed(() => ({
  SCHEDULED: 'pill-blue', PENDING: 'pill-amber', ONGOING: 'pill-green', FINISHED: 'pill-gray', SYSTEM_FINISHED: 'pill-gray',
  CANCELLED: 'pill-red', REJECTED: 'pill-red', NO_SHOW: 'pill-red',
}[lesson.value?.status || 'SCHEDULED'] || 'pill-gray'))

const phaseIcon = computed(() => ({ live: 'board', soon: 'clock', upcoming: 'calendar', request: 'info', over: 'check', closed: 'info' }[phase.value.kind]))
const phaseTitle = computed(() => {
  const p = phase.value
  if (p.kind === 'live') return 'Урок идёт сейчас'
  if (p.kind === 'soon') return `Начнётся через ${durationText(p.minutes)}`
  if (p.kind === 'upcoming') return `До начала ${durationText(p.minutes)}`
  if (p.kind === 'request') return isTutor.value ? 'Заявка ждёт вашего решения' : 'Заявка ждёт подтверждения репетитора'
  if (p.kind === 'over') return 'Урок прошёл'
  return lesson.value?.status === 'REJECTED' ? 'Заявка отклонена' : lesson.value?.status === 'NO_SHOW' ? 'Отмечена неявка' : 'Урок отменён'
})
const phaseHint = computed(() => {
  const p = phase.value
  if (p.kind === 'live') return `До конца ${durationText(p.minutes)}.`
  if (p.kind === 'over' && isTutor.value && canMark.value) return 'Отметьте, как прошёл урок: это попадёт в оплаты и статистику.'
  if (p.kind === 'request' && p.minutes) return `Начало через ${durationText(p.minutes)}.`
  return ''
})

const MARK_COPY = {
  FINISHED: { title: 'Отметить урок проведённым?', text: 'Урок попадёт в оплаты и статистику. Ученики получат уведомление.', label: 'Урок проведён', placeholder: 'Комментарий (необязательно)' },
  NO_SHOW: { title: 'Отметить неявку?', text: 'Ученики получат уведомление. Отметка попадёт в историю урока.', label: 'Отметить неявку', placeholder: 'Например: не вышел на связь' },
  CANCELLED: { title: 'Отменить урок?', text: 'Все записи будут отменены, ученики получат уведомление с причиной.', label: 'Отменить урок', placeholder: 'Например: заболел, перенесём на следующую неделю' },
}
const markCopy = computed(() => MARK_COPY[markStatusValue.value])
function markDialog(status) {
  markStatusValue.value = status
  decisionError.value = ''
  markRef.value?.open()
}

async function onMark(reason) {
  if (await markStatus(markStatusValue.value, reason)) markRef.value?.close()
}
async function onCancel(reason) {
  if (await cancelAsStudent(reason)) cancelDialog.value?.close()
}
async function onReject(reason) {
  if (await rejectRequest(reason)) rejectDialog.value?.close()
}
</script>

<style scoped>
.lesson-page { padding-bottom: 32px; }
.lesson-page .toolbar h1 { font-size: 26px; margin: 4px 0 2px; }
.lesson-page .lead { margin: 0; }
.back { font-size: 13px; color: var(--muted); }

.join { display: grid; gap: 16px; padding: 22px 24px; border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--surface); margin-bottom: 16px; }
.join--live { border-color: var(--ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 18%, transparent); }
.join--soon { border-color: var(--accent); }
.join--closed, .join--over { background: var(--bg); }
.join-state { display: flex; gap: 14px; align-items: center; }
.join-icon { width: 44px; height: 44px; flex: none; display: grid; place-items: center; border-radius: 12px; background: var(--accent-soft); color: var(--accent); }
.join--live .join-icon { background: color-mix(in srgb, var(--ok) 16%, transparent); color: var(--ok); }
.join--closed .join-icon { background: color-mix(in srgb, var(--danger) 14%, transparent); color: var(--danger); }
.join-icon :deep(svg) { width: 22px; height: 22px; }
.join-title { font-size: 20px; margin: 0; letter-spacing: -.01em; }
.join--live .join-title::before { content: ""; display: inline-block; width: 9px; height: 9px; margin-right: 8px; border-radius: 50%; background: var(--ok); vertical-align: middle; animation: pulse 1.6s ease-in-out infinite; }
.join-hint { margin: 2px 0 0; color: var(--muted); font-size: 13.5px; }
.join-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.join-actions .btn.big { height: 46px; padding: 0 22px; font-size: 15px; }
.join-decide { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding-top: 14px; border-top: 1px solid var(--line); margin: 0; }
.danger-text { color: var(--danger); }
@keyframes pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .join--live .join-title::before { animation: none; } }

.notes { margin-bottom: 16px; }
.lesson-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 16px; align-items: start; }
.lesson-main { display: grid; gap: 16px; min-width: 0; }
.lesson-side { display: grid; gap: 16px; }
.panel h3 { margin: 0 0 12px; font-size: 15px; }
.panel-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.panel-head h3 { margin: 0; }
.total { color: var(--text); }
.people { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.people li { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.people li:last-child { border-bottom: 0; }
.people li.cancelled strong { color: var(--muted); text-decoration: line-through; }
.pay { height: 30px; padding: 0 12px; border-radius: 999px; border: 1px solid var(--line-strong); background: var(--surface-2); color: var(--muted); font: 500 12.5px var(--sans); cursor: pointer; white-space: nowrap; }
.pay:hover:not(:disabled) { border-color: var(--accent); color: var(--text); }
.pay.on { background: color-mix(in srgb, var(--ok) 16%, transparent); border-color: var(--ok); color: var(--ok); }
.pay:disabled { opacity: .6; cursor: not-allowed; }
.add-part { gap: 8px; margin-top: 12px; }
.add-part select { flex: 1; min-width: 0; }
.side-card { display: grid; gap: 10px; }
.side-card .btn { justify-content: flex-start; }
.link-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.link-list li { display: flex; align-items: center; gap: 8px; font-size: 13.5px; }
.li-ico { width: 15px; height: 15px; color: var(--muted); flex: none; }
.attach { font-size: 13px; }
.lesson-grid--solo { grid-template-columns: minmax(0, 1fr); }
.lesson-grid--solo .side-card { display: flex; flex-wrap: wrap; align-items: center; }
.lesson-grid--solo .side-card h2 { flex: 1 0 100%; }
.lesson-grid--solo .side-card .btn { width: auto; }
@media (max-width: 900px) { .lesson-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 600px) {
  .join { padding: 18px 16px; }
  .join-actions .btn { width: 100%; }
  .join-decide .btn { flex: 1 1 auto; }
}
</style>
