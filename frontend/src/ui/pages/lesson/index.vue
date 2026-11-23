<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="lesson-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Урок</h1>
          <div class="page-actions">
            <router-link to="/schedule" class="btn btn--gry btn--sm">К расписанию</router-link>
            <button v-if="isTutor && lesson" type="button" class="btn btn--dan btn--sm" :disabled="busy" @click="handleDelete">
              Удалить
            </button>
          </div>
        </div>
        <p class="page-desc">{{ lesson ? `${lessonDateLabel(lesson.start_time)} · ${lessonTimeLabel(lesson.start_time, lesson.end_time)}` : 'Загрузка...' }}</p>
      </div>

      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="error" class="fmsg fmsg--err">{{ error }}</div>

      <template v-else-if="lesson">
        <section class="card">
          <h2 class="card-title">Детали</h2>
          <div class="info-grid">
            <div class="info-r">
              <span class="info-k">Статус</span>
              <span class="info-v">
                <span class="status-chip" :style="{ color: statusColor(lesson.status) }">{{ statusLabel(lesson.status) }}</span>
              </span>
            </div>
            <div class="info-r">
              <span class="info-k">Тип</span>
              <span class="info-v">{{ lesson.is_group ? 'Групповой' : 'Индивидуальный' }}</span>
            </div>
            <div v-if="!isTutor" class="info-r">
              <span class="info-k">Репетитор</span>
              <span class="info-v">{{ tutorName }}</span>
            </div>
            <div v-if="isTutor && lesson.descriptions" class="info-r info-r--full">
              <span class="info-k">Описание</span>
              <span class="info-v">{{ lesson.descriptions }}</span>
            </div>
          </div>

          <div v-if="safeLinks.length" class="links-row">
            <span class="info-k">Ссылки</span>
            <a v-for="l in safeLinks" :key="l.safe" :href="l.safe" target="_blank" rel="noopener noreferrer" class="link-btn">
              {{ l.alias }}
            </a>
          </div>
        </section>

        <section v-if="isTutor" class="card">
          <h2 class="card-title">Участники ({{ lesson.students?.length || 0 }})</h2>
          <div v-if="!lesson.students?.length" class="empty">Участников нет</div>
          <div v-else class="table-wrap">
            <table class="part-table">
              <thead>
                <tr>
                  <th>Ученик</th>
                  <th class="col-num">Сумма</th>
                  <th>Оплата</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in lesson.students" :key="s.student_id">
                  <td>
                    {{ s.student_name }}
                    <span v-if="s.cancelled" class="part-cancel">(отменена: {{ s.cancelled_by === 'student' ? 'учеником' : 'репетитором' }})</span>
                  </td>
                  <td class="col-num">{{ formatMoney(s.amount) }}</td>
                  <td>
                    <button
                      type="button"
                      class="pay-toggle"
                      :class="{ 'pay-toggle--on': s.paid }"
                      :disabled="busy || s.cancelled"
                      @click="togglePaid(s)"
                    >
                      {{ s.paid ? 'Оплачено' : 'Не оплачено' }}
                    </button>
                  </td>
                  <td class="col-act">
                    <button
                      v-if="!s.cancelled"
                      type="button"
                      class="btn btn--gry btn--xs"
                      :disabled="busy"
                      title="Убрать с урока"
                      @click="removeParticipant(s)"
                    >
                      Убрать
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="add-part">
            <select v-model="newParticipant" :disabled="busy">
              <option value="">Выберите ученика</option>
              <option v-for="s in roster" :key="s.user_id" :value="String(s.user_id)">
                {{ s.full_name || `Ученик #${s.user_id}` }}
              </option>
            </select>
            <button type="button" class="btn btn--pri btn--sm" :disabled="busy || !newParticipant" @click="addParticipant">
              Добавить
            </button>
          </div>
        </section>

        <p v-if="isTutor" class="total-line">
          Итого за урок: <strong>{{ formatMoney(lesson.total) }}</strong>
        </p>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { useLessonPage } from './useLessonPage.js'
import { useRosterStore } from '../../../logic/store/index.js'
import { lessonSafeLinks, tutorNameOf, lessonDateLabel, lessonTimeLabel } from '../../../logic/utils/index.js'
import { formatMoney } from '../../../logic/utils/index.js'
import { LESSON_STATUSES } from '../../../logic/constants/index.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const rosterStore = useRosterStore()
const {
  lesson, loading, error, busy, isTutor, roster, newParticipant,
  togglePaid, addParticipant, removeParticipant, handleDelete,
} = useLessonPage()

const safeLinks = computed(() => lessonSafeLinks(lesson.value?.links))
const tutorName = computed(() => tutorNameOf(lesson.value, rosterStore.tutors))

function statusLabel(status) {
  return LESSON_STATUSES.find((s) => s.value === status)?.label || status
}
function statusColor(status) {
  return LESSON_STATUSES.find((s) => s.value === status)?.color || 'var(--color-gray-600)'
}
</script>

<style scoped>
.page-actions { display: flex; gap: 8px; }
.card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  padding: 16px;
  margin-bottom: 16px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--color-primary); margin-bottom: 12px; }
.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.info-r { display: flex; flex-direction: column; gap: 4px; }
.info-r--full { grid-column: 1 / -1; }
.info-k { font-size: 10px; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; color: var(--color-gray-500); }
.info-v { font-size: 14px; font-weight: 500; color: var(--color-gray-800); }
.status-chip { font-size: 14px; font-weight: 600; }
.links-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; }
.link-btn {
  padding: 4px 10px;
  border: 1px solid var(--color-gray-300);
  border-radius: var(--radius-md, 6px);
  font-size: 13px;
  color: var(--color-accent);
  text-decoration: none;
}
.link-btn:hover { border-color: var(--color-accent); }
.table-wrap { overflow-x: auto; }
.part-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.part-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--color-gray-500);
  border-bottom: 2px solid var(--color-gray-200);
}
.part-table td { padding: 8px 10px; border-bottom: 1px solid var(--color-gray-100); color: var(--color-gray-800); }
.col-num { text-align: right; font-variant-numeric: tabular-nums; }
.col-act { text-align: right; }
.part-cancel { font-size: 11px; color: var(--color-danger); }
.pay-toggle {
  padding: 3px 8px;
  border: 1px solid var(--color-gray-300);
  border-radius: var(--radius-md, 6px);
  background: var(--color-white);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-gray-600);
  cursor: pointer;
}
.pay-toggle:hover:not(:disabled) { border-color: var(--color-accent); color: var(--color-accent); }
.pay-toggle--on { background: var(--color-success); border-color: var(--color-success); color: var(--color-white); }
.pay-toggle--on:hover:not(:disabled) { border-color: var(--color-success); color: var(--color-white); }
.pay-toggle:disabled { opacity: 0.6; cursor: not-allowed; }
.add-part { display: flex; gap: 8px; margin-top: 12px; }
.add-part select { flex: 1; min-width: 0; }
.total-line { font-size: 14px; color: var(--color-gray-600); }
.empty { padding: 20px; text-align: center; font-size: 14px; color: var(--color-gray-500); }
</style>
