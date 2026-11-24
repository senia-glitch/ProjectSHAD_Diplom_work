<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp boards-page">
      <div class="page-head">
        <h1>Доски</h1>
        <p class="lead">Совместное рисование на занятии: до 15 участников, общий чат, автосохранение.
          {{ role === 'tutor' ? 'Создайте доску и сообщите ученику код.' : 'Введите код, который сообщил репетитор.' }}</p>
      </div>

      <div class="boards-forms">
        <form class="form-card stack-sm" @submit.prevent="handleJoin">
          <h2>Войти по коду</h2>
          <label>Код доски
            <input v-model="code" type="text" maxlength="64" autocomplete="off" autocapitalize="characters"
                   spellcheck="false" placeholder="например, 8P4H5XYU" required>
          </label>
          <p class="error-text" role="alert">{{ joinError }}</p>
          <div class="row"><button class="btn primary" type="submit" :disabled="joining">Войти</button></div>
        </form>

        <form v-if="role === 'tutor'" class="form-card stack-sm" @submit.prevent="handleCreate">
          <h2>Новая доска</h2>
          <label>Название <input v-model="title" type="text" maxlength="120" placeholder="Урок 1: дроби"></label>
          <label>Свой код <span class="hint">необязательно: от 6 букв или цифр, иначе сгенерируется</span>
            <input v-model="customCode" type="text" maxlength="32" autocomplete="off" spellcheck="false">
          </label>
          <p class="error-text" role="alert">{{ createError }}</p>
          <div class="row">
            <button class="btn primary" type="submit" :disabled="creating">Создать доску</button>
            <button class="btn ghost" type="button" :disabled="creating" @click="fileInput?.click()">Из файла…</button>
            <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="handleFile">
          </div>
        </form>
      </div>

      <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>
      <div v-else-if="loading" class="skeleton" aria-hidden="true"></div>
      <template v-else>
        <section v-if="role === 'tutor'" class="stack-sm boards-section">
          <h2>Мои доски</h2>
          <div v-if="!mine.length" class="empty"><p class="muted">Досок пока нет. Создайте первую — код появится сразу.</p></div>
          <div v-else class="cards">
            <article v-for="b in mine" :key="b.id" class="tcard">
              <h3><router-link class="card-link" :to="`/boards/${b.id}`">{{ b.title || 'Без названия' }}</router-link></h3>
              <div class="meta-row">
                <span>{{ b.stroke_count }} {{ strokesWord(b.stroke_count) }}</span>
                <span>активность: {{ formatDate(b.last_active_at) }}</span>
              </div>
              <div class="card-actions">
                <router-link class="ibtn" :to="`/boards/${b.id}`" data-tip="Открыть" aria-label="Открыть доску"><UiIcon name="open" /></router-link>
                <button class="ibtn danger" type="button" data-tip="Удалить" :aria-label="`Удалить доску ${b.title}`" @click="handleDelete(b)"><UiIcon name="trash" /></button>
              </div>
            </article>
          </div>
        </section>

        <section class="stack-sm boards-section">
          <h2>{{ role === 'tutor' ? 'Доски коллег, где я участник' : 'Мои доски' }}</h2>
          <div v-if="!joined.length" class="empty"><p class="muted">Здесь появятся доски, на которые вы входили по коду.</p></div>
          <div v-else class="cards">
            <article v-for="b in joined" :key="b.id" class="tcard">
              <h3><router-link class="card-link" :to="`/boards/${b.id}`">{{ b.title || 'Без названия' }}</router-link></h3>
              <div class="meta-row"><span>{{ b.owner_name }}</span><span>активность: {{ formatDate(b.last_active_at) }}</span></div>
            </article>
          </div>
        </section>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon } from '../../components/index.js'
import { useLogout, useUser } from '../../composables/index.js'
import { findBoardByCode, loadBoards, openNewBoard, removeBoard, uploadBoardFile } from '../../../logic/actions/index.js'
import { readBoardFile, rememberBoardCode, rememberCreatedBoard, strokesWord } from '../../legacy/board/board.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'

const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()

const mine = ref([])
const joined = ref([])
const loading = ref(true)
const loadError = ref('')
const code = ref('')
const joining = ref(false)
const joinError = ref('')
const title = ref('')
const customCode = ref('')
const creating = ref(false)
const createError = ref('')
const fileInput = ref(null)

function formatDate(value) {
  try { return new Date(value).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) } catch { return '' }
}

async function refresh() {
  loadError.value = ''
  try {
    const data = await loadBoards(role.value)
    mine.value = data.mine
    joined.value = data.joined
  } catch (e) {
    loadError.value = e.message || 'Не удалось загрузить доски'
  } finally {
    loading.value = false
  }
}

async function handleJoin() {
  joinError.value = ''
  joining.value = true
  try {
    const board = await findBoardByCode(code.value.trim())
    rememberBoardCode(board.id, code.value.trim())
    router.push(`/boards/${board.id}`)
  } catch (e) {
    joinError.value = e.message || 'Доска не найдена'
  } finally {
    joining.value = false
  }
}

async function handleCreate() {
  createError.value = ''
  creating.value = true
  try {
    const board = await openNewBoard(title.value.trim(), customCode.value.trim())
    rememberCreatedBoard(board.id, board.code)
    router.push(`/boards/${board.id}`)
  } catch (e) {
    createError.value = e.message || 'Не удалось создать доску'
  } finally {
    creating.value = false
  }
}

async function handleFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  createError.value = ''
  creating.value = true
  try {
    const data = await readBoardFile(file)
    const board = await openNewBoard((data.title || title.value || file.name.replace(/\.(doska\.)?json$/i, '')).slice(0, 120), customCode.value.trim())
    await uploadBoardFile(board.id, { mode: 'replace', code: board.code, name: '', board: data })
    rememberCreatedBoard(board.id, board.code)
    router.push(`/boards/${board.id}`)
  } catch (e) {
    createError.value = e.message || 'Не удалось загрузить файл'
  } finally {
    creating.value = false
  }
}

async function handleDelete(board) {
  const ok = await askConfirm(`Удалить доску «${board.title || 'Без названия'}»?`,
    'Рисунок, чат и список участников будут удалены безвозвратно. Участники на доске будут отключены.',
    { okText: 'Удалить', danger: true })
  if (!ok) return
  try {
    await removeBoard(board.id)
    mine.value = mine.value.filter((b) => b.id !== board.id)
    toast('Доска удалена', 'ok')
  } catch (e) {
    toast(e.message || 'Не удалось удалить доску', 'error')
  }
}

onMounted(() => {
  document.title = 'Доски · SHAD'
  refresh()
})
</script>

<style scoped>
.boards-forms { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; align-items: start; margin-bottom: 40px; }
.boards-forms h2 { margin: 0; font-size: 1.05rem; }
.boards-section { margin-bottom: 40px; }
.boards-section h2 { margin: 0; }
.tcard h3 { font-size: 1.05rem; margin: 0; }
.pp .ibtn :deep(.ui-icon) { width: 17px; height: 17px; }
</style>
