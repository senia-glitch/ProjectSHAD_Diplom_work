<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp blog-editor">
      <div class="toolbar">
        <div>
          <router-link class="back" to="/blog/manage">← Мой блог</router-link>
          <h1>{{ postId ? 'Редактирование записи' : 'Новая запись' }}</h1>
        </div>
        <div class="row">
          <button type="button" class="btn ghost" :disabled="saving" @click="save('draft')">Сохранить черновик</button>
          <button type="button" class="btn primary" :disabled="saving" @click="save('published')">
            {{ form.status === 'published' && postId ? 'Сохранить' : 'Опубликовать' }}
          </button>
        </div>
      </div>

      <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>
      <div v-else class="split">
        <form class="form-card stack-sm" @submit.prevent="save(form.status)">
          <label>Заголовок <input v-model="form.title" type="text" maxlength="200" required></label>
          <label>Текст
            <span ref="toolbarSlot" class="md-toolbar-slot"></span>
            <textarea ref="bodyArea" v-model="form.body" class="editor" maxlength="50000" @input="dirty = true"></textarea>
            <span class="hint">Markdown: заголовки, списки, ссылки, код. Картинки и видео — по внешним ссылкам.</span>
          </label>
          <label>Теги <input v-model="tagsText" type="text" maxlength="300" placeholder="егэ, математика, советы">
            <span class="hint">Через запятую, до 8 тегов</span>
          </label>
          <label class="check"><input v-model="form.pinned" type="checkbox"> Закрепить вверху моего блога</label>
          <p v-if="form.status === 'published'" class="hint">Запись опубликована. «Сохранить черновик» снимет её с публикации.</p>
          <div v-if="error" class="notice error" role="alert">{{ error }}</div>
        </form>
        <section class="preview" aria-label="Предпросмотр">
          <h3 class="preview-title">Предпросмотр</h3>
          <h2 class="preview-heading">{{ form.title || 'Заголовок записи' }}</h2>
          <MarkdownView :source="form.body || '_Текст появится здесь._'" />
          <div v-if="tags.length" class="tags"><span v-for="t in tags" :key="t" class="tag static">#{{ t }}</span></div>
        </section>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import MarkdownView from '../../components/MarkdownView.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { loadPost, savePost } from '../../../logic/actions/index.js'
import { askConfirm, mdToolbar, toast } from '../../legacy/testing/kit.js'

const route = useRoute()
const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()

const postId = computed(() => (route.params.id ? Number(route.params.id) : null))
const form = reactive({ title: '', body: '', status: 'draft', pinned: false })
const tagsText = ref('')
const tags = computed(() => [...new Set(tagsText.value.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean))])
const saving = ref(false)
const error = ref('')
const loadError = ref('')
const dirty = ref(false)
const bodyArea = ref(null)
const toolbarSlot = ref(null)
let snapshot = ''

const state = () => JSON.stringify({ ...form, tags: tags.value })

async function save(status) {
  error.value = ''
  if (!form.title.trim()) { error.value = 'Укажите заголовок'; return }
  saving.value = true
  try {
    const saved = await savePost(postId.value, { title: form.title, body: form.body, tags: tags.value, status, pinned: form.pinned })
    form.status = saved.status
    snapshot = state()
    toast(status === 'published' ? 'Запись опубликована' : 'Черновик сохранён', 'ok')
    if (!postId.value) router.replace(`/blog/manage/${saved.id}`)
    document.title = 'Редактирование · Блог · SHAD'
  } catch (e) {
    error.value = e.message || 'Не удалось сохранить'
  } finally {
    saving.value = false
  }
}

function beforeUnload(event) {
  if (state() !== snapshot) { event.preventDefault(); event.returnValue = '' }
}

onBeforeRouteLeave(async (to) => {
  if (to.name === 'blog-edit' || state() === snapshot) return true
  return askConfirm('Уйти со страницы?', 'Есть несохранённые изменения.', { okText: 'Уйти', danger: true, cancelText: 'Остаться' })
})

onMounted(async () => {
  window.addEventListener('beforeunload', beforeUnload)
  document.title = `${postId.value ? 'Редактирование' : 'Новая запись'} · Блог · SHAD`
  if (postId.value) {
    try {
      const { post } = await loadPost(postId.value)
      Object.assign(form, { title: post.title, body: post.body, status: post.status, pinned: post.pinned })
      tagsText.value = post.tags.join(', ')
    } catch (e) {
      loadError.value = e.message || 'Запись не найдена'
    }
  }
  snapshot = state()
  await nextTick()
  if (bodyArea.value && toolbarSlot.value) {
    // Панель Markdown из модуля тестирования вставляет разметку в textarea и генерирует input.
    toolbarSlot.value.replaceWith(mdToolbar(bodyArea.value))
    bodyArea.value.addEventListener('input', () => { form.body = bodyArea.value.value })
  }
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
</script>

<style scoped>
.preview-heading { margin: 0 0 12px; font-size: 1.35rem; }
.check { display: flex; align-items: center; gap: 8px; flex-direction: row; }
.check input { width: auto; }
.preview .tags { margin-top: 16px; }
</style>
