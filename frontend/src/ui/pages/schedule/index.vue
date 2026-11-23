<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="schedule-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Расписание</h1>
          <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
        </div>
        <p class="page-desc">Управление уроками по дням недели</p>
      </div>
      <ScheduleTour v-if="showTour" @close="showTour = false" />

      <div class="view-toggle">
        <button
          v-for="m in viewModes" :key="m.value"
          type="button"
          :class="viewMode === m.value ? 'view-toggle--on' : ''"
          @click="viewMode = m.value"
        >{{ m.label }}</button>
      </div>

      <div v-if="viewMode === 'calendar'">
        <div v-if="calendarLoading" class="loading">Загрузка...</div>
        <div v-else-if="calendarError" class="state-box state-box--warn">
          <p>{{ calendarError }}</p>
        </div>
        <div v-else>
          <div class="cal-toolbar">
            <button type="button" class="btn btn--sm btn--gry" @click="calendarShift(-1)">&larr;</button>
            <span class="cal-month">{{ calendarMonthLabel }}</span>
            <button type="button" class="btn btn--sm btn--gry" @click="calendarShift(1)">&rarr;</button>
            <button type="button" class="btn btn--sm btn--gry" @click="calendarGoToday">Сегодня</button>
          </div>
          <MonthGrid
            :weeks="calendarWeeks"
            :counts="calendarCounts"
            :selected-day="calendarSelectedDay"
            :today-iso="calendarTodayIso"
            @pick="calendarPickDay"
          />
          <div v-if="calendarSelectedDay" class="day-list">
            <h3>Уроки на {{ calendarSelectedDay }}</h3>
            <div v-if="calendarDayLessons.length" class="day-cards">
              <router-link
                v-for="lesson in calendarDayLessons" :key="lesson.lesson_id"
                :to="`/lessons/${lesson.lesson_id}`"
                class="lesson-card"
              >
                <span class="lesson-time">{{ lesson.start }}–{{ lesson.end }}</span>
                <span class="lesson-status" :class="`status-${lesson.status}`">{{ statusLabel(lesson.status) }}</span>
              </router-link>
            </div>
            <p v-else class="empty-text">Нет уроков на этот день</p>
          </div>
        </div>
      </div>

      <template v-else>
        <div v-if="loading" class="loading">Загрузка...</div>
        <div v-else class="schedule-layout">
          <div class="side-col" :style="colStyle">
            <ScheduleInfoPanel
              :role="role"
              :lessons="lessons"
              :selected-ids="selectedIds"
              :editing-id="editingId"
              :edit-form="editForm"
              :edit-errors="editErrors"
              :edit-msg="editMsg"
              :edit-err="editErr"
              :participants-map="participantsMap"
              :participants-loading="participantsLoading"
              :edit-rows="editRows"
              :add-participant-err="addParticipantErr"
              :students="students"
              :tutors="tutors"
              :saving="saving"
              @start-edit="startEdit"
              @delete-lesson="handleDelete"
              @save-lesson="handleUpdate"
              @cancel-edit="cancelEdit"
              @row-add="addEditRow"
              @row-remove="removeEditRow"
              @single-pick="singlePick"
              @load-participants="loadParticipants"
              @link-add="addEditLink"
              @link-remove="removeEditLink"
              @links-from-config="applyLinksFromConfig"
              @links-to-config="applyLinksToConfig"
              @links-from-settings="applyLinksFromSettings"
              @links-to-settings="applyLinksToSettings"
            />
          </div>
          <ScheduleGrid
            :lessons="lessons"
            :dim-bookings="dimBookings"
            :free-windows="role === 'student' ? freeWindows : []"
            :tutor-colors="role === 'student' ? resolvedTutorColors : {}"
            :outlined-weekdays="role === 'student' ? outlinedWeekdays : []"
            :preview-blocks="previewBlocks"
            :week-days="weekDays"
            :visible-hours="visibleHours"
            :dynamic-grid-h="dynamicGridH"
            :selected-ids="selectedIds"
            @lesson-select="toggleSelect"
            @grid-clear="clearSelection"
            @nav-prev="prevWeek"
            @nav-next="nextWeek"
            @nav-today="goToday"
            @grid-ready="bindGridBox"
          />
          <div v-if="role === 'tutor'" class="side-col side-col--wide" :style="colStyle">
            <LessonCreator
              :slots="createSlots"
              :students="students"
              v-model:saving="saving"
              @clear="clearCreateForm"
            />
          </div>
          <div v-else-if="role === 'student'" class="side-col side-col--wide" :style="colStyle">
            <StudentLessonCreator
              :slots="createSlots"
              :tutors="tutors"
              :tutor-colors="resolvedTutorColors"
              :week-range="weekRange"
              v-model:saving="saving"
              @clear="clearCreateForm"
              @ensure-color="ensureTutorColor"
              @set-color="setTutorColor"
            />
          </div>
        </div>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import ScheduleGrid from './ScheduleGrid.vue'
import ScheduleInfoPanel from './ScheduleInfoPanel.vue'
import LessonCreator from './LessonCreator.vue'
import StudentLessonCreator from './StudentLessonCreator.vue'
import ScheduleTour from './ScheduleTour.vue'
import MonthGrid from '../calendar/MonthGrid.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { useSchedulePage } from './useSchedulePage.js'
import { useSideHeights } from './useSideHeights.js'
import { useCalendarPage } from '../calendar/useCalendarPage.js'
import { LESSON_STATUSES } from '../../../logic/constants/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const { colStyle, bindGridBox } = useSideHeights()
const showTour = ref(false)

const viewMode = ref('week')
const viewModes = [
  { value: 'week', label: 'Неделя' },
  { value: 'calendar', label: 'Календарь' },
]

const {
  year, month, calendarSelectedDay,
  lessons: calendarLessons,
  loading: calendarLoading,
  error: calendarError,
  monthLabel: calendarMonthLabel,
  counts: calendarCounts,
  weeks: calendarWeeks,
  dayLessonsList: calendarDayLessons,
  shift: calendarShift,
  goToday: calendarGoToday,
  pickDay: calendarPickDay,
} = useCalendarPage()

const calendarTodayIso = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

function statusLabel(status) {
  const found = LESSON_STATUSES.find((s) => s.value === status)
  return found ? found.label : status
}

watch(viewMode, (mode) => {
  if (mode === 'calendar') {
    calendarGoToday()
  }
})
const {
  lessons,
  students,
  tutors,
  resolvedTutorColors,
  outlinedWeekdays,
  weekRange,
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
  toggleSelect,
  clearSelection,
  loadParticipants,
  startEdit,
  cancelEdit,
  handleUpdate,
  handleDelete,
  addEditRow,
  removeEditRow,
  singlePick,
  addEditLink,
  removeEditLink,
  applyLinksFromConfig,
  applyLinksToConfig,
  applyLinksFromSettings,
  applyLinksToSettings,
  clearCreateForm,
  ensureTutorColor,
  setTutorColor,
} = useSchedulePage()
</script>

<style scoped>
.schedule-page { display: flex; flex-direction: column; gap: 16px; }
.view-toggle { display: inline-flex; background: var(--color-gray-100); border-radius: 9px; padding: 3px; gap: 2px; align-self: flex-start; }
.view-toggle button { border: none; background: none; cursor: pointer; font-size: 13px; font-weight: 500; color: var(--color-gray-600); padding: 6px 16px; border-radius: 7px; white-space: nowrap; }
.view-toggle button.view-toggle--on { background: var(--color-white); color: var(--color-gray-800); box-shadow: var(--shadow-sm); }
.cal-toolbar { display: flex; align-items: center; gap: 8px; }
.cal-month { font-size: 16px; font-weight: 600; }
.day-list { margin-top: 16px; }
.day-list h3 { margin: 0 0 12px; font-size: 16px; }
.day-cards { display: flex; flex-direction: column; gap: 8px; }
.lesson-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: var(--color-white); border: 1px solid var(--color-gray-200); border-radius: var(--radius-lg); text-decoration: none; color: var(--color-gray-800); }
.lesson-card:hover { border-color: var(--color-accent); }
.lesson-time { font-weight: 600; }
.lesson-status { margin-left: auto; font-size: 12px; padding: 2px 8px; border-radius: var(--radius-full); }
.status-SCHEDULED { background: var(--color-gray-100); color: var(--color-gray-600); }
.status-FINISHED { background: #e8f5e9; color: #2e7d32; }
.status-CANCELLED { background: #ffebee; color: #c62828; }
.empty-text { color: var(--color-gray-600); font-size: 14px; }
.state-box { background: var(--color-white); border: 1px solid var(--color-gray-200); border-radius: var(--radius-lg); padding: 28px 20px; text-align: center; color: var(--color-gray-600); font-size: 14px; }
.state-box p { margin: 0; }
.state-box--warn { padding: 12px 16px; }
.schedule-layout { display: flex; gap: 20px; flex: 1; align-items: stretch; }
</style>
