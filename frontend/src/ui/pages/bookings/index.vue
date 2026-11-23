<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="bookings-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">График броней</h1>
          <button type="button" class="help-btn" title="Как пользоваться страницей" @click="showTour = true">?</button>
        </div>
        <p class="page-desc">Правила доступа к вашему времени</p>
      </div>
      <BookingTour v-if="showTour" @close="showTour = false" />

      <div v-if="loading" class="loading">Загрузка...</div>

      <div v-else class="bookings-layout">
        <BookingGrid
          :bookings="bookings"
          :preview-bookings="previewBookings"
          :selected-id="selected?.id ?? null"
          @select-booking="selectBooking"
          @grid-click="onGridPick"
        />
        <aside class="workspace-tools" aria-label="Управление бронями">
          <div class="side-col side-col--wide">
            <!-- === CREATE FORM === -->
            <BookingCreator
              ref="creatorRef"
              :slots="createSlots"
              :students="students"
              :bookings="bookings"
              v-model:saving="saving"
              @pick-student="openCreatePicker"
            />

            <!-- === STUDENT PICKER MODAL === -->
            <Teleport to="body">
              <div v-if="studentPicker.show" class="modal-overlay" @click.self="closeStudentPicker">
                <div class="modal" role="dialog" aria-modal="true" aria-labelledby="bookings-student-picker-title">
                  <h3 id="bookings-student-picker-title" class="modal-title">Выберите ученика</h3>
                  <div v-if="!students.length" class="modal-empty">Нет учеников</div>
                  <div v-else class="modal-list">
                      <button
                        v-for="s in availableStudents()"
                        :key="s.student_id"
                      type="button"
                      class="modal-item"
                      @click="pickStudent(s.student_id)"
                    >{{ s.full_name }}</button>
                      <div v-if="!availableStudents().length" class="modal-empty">Все ученики уже добавлены</div>
                  </div>
                  <div class="modal-actions">
                    <button type="button" class="btn btn--gry" @click="closeStudentPicker">Отмена</button>
                  </div>
                </div>
              </div>
            </Teleport>

          </div>
          <div class="side-col">
            <BookingInfoPanel
              :selected="selected"
              :editing="editing"
              :edit-form="editForm"
              :edit-errors="editErrors"
              :edit-msg="editMsg"
              :edit-err="editErr"
              :delete-err="deleteErr"
              :update-msg="updateMsg"
              :students="students"
              :saving="saving"
              @start-edit="startEdit"
              @delete="handleDelete"
              @save="handleUpdate"
              @cancel="cancelEdit"
              @open-picker="openEditPicker"
              @remove-target="removeEditTarget"
            />
          </div>
          </aside>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import BookingGrid from './BookingGrid.vue'
import BookingInfoPanel from './BookingInfoPanel.vue'
import BookingCreator from './BookingCreator.vue'
import BookingTour from './BookingTour.vue'
import { useUser, useLogout, useEscapeKey } from '../../composables/index.js'
import { useBookingsPage } from './useBookingsPage.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const creatorRef = ref(null)
const showTour = ref(false)

function onGridPick(payload) {
  prefillCreateSlot(payload)
  creatorRef.value?.clearErrors()
}
const {
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
  openEditPicker,
  openCreatePicker,
  removeEditTarget,
  closeStudentPicker,
  pickStudent,
  availableStudents,
  prefillCreateSlot,
  handleUpdate,
  handleDelete,
} = useBookingsPage()

useEscapeKey(() => studentPicker.show, closeStudentPicker)
</script>

<style scoped>


.bookings-page { display: flex; flex-direction: column; }
/* Имя класса уникально для страницы: общий `.layout` конфликтовал
   с корнем MainLayout (наследование scope-атрибута) и ломал шапку сайта. */
/* Три колонки как на странице расписания: инфо слева 240, сетка в центре,
   создание справа 384. Высоты равные по умолчанию за счёт stretch. */
.bookings-layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }

.workspace-tools { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
@media (max-width: 1000px) {
  .workspace-tools { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; }
}
@media (max-width: 600px) {
  .workspace-tools { display: flex; }
}

@media (max-width: 1000px) {
  .bookings-layout { grid-template-columns: minmax(0, 1fr); }
}
</style>
