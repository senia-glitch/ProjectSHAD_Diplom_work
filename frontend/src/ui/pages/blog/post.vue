<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp blog-post">
      <div v-if="error" class="notice error" role="alert">
        {{ error }} <router-link to="/blog">К блогу</router-link>
      </div>
      <div v-else-if="!post" class="skeleton tall" aria-hidden="true"></div>
      <article v-else class="post">
        <router-link class="back" :to="`/blog/authors/${post.author_id}`">← Блог: {{ post.author_name }}</router-link>
        <h1 class="post-title">{{ post.title }}</h1>
        <div class="meta post-meta">
          <span class="avatar small" aria-hidden="true">{{ initials(post.author_name) }}</span>
          <router-link :to="`/blog/authors/${post.author_id}`">{{ post.author_name }}</router-link>
          <span>{{ post.status === 'published' ? formatDate(post.published_at) : 'Черновик — видите только вы' }}</span>
          <span v-if="post.status !== 'published'" class="badge draft">черновик</span>
          <router-link v-if="isAuthor" class="btn small ghost" :to="`/blog/manage/${post.id}`">
            <UiIcon name="edit" class="btn-ico" /> Изменить
          </router-link>
        </div>
        <MarkdownView :source="post.body" />
        <div v-if="post.tags.length" class="tags post-tags">
          <router-link v-for="t in post.tags" :key="t" class="tag" :to="{ path: `/blog/authors/${post.author_id}`, query: { tag: t } }">#{{ t }}</router-link>
        </div>

        <section v-if="post.status === 'published'" class="comments" aria-labelledby="comments-title">
          <h2 id="comments-title">Комментарии <span class="muted">{{ comments.length }}</span></h2>
          <p v-if="!comments.length" class="muted">Комментариев пока нет.</p>
          <div v-for="c in comments" :key="c.id" class="comment">
            <div class="comment-head">
              <span><strong>{{ c.author_name }}</strong> <span v-if="c.author_id === post.author_id" class="badge">автор</span>
                <span v-else-if="c.author_role === 'student'" class="muted"> · ученик</span></span>
              <span class="row-actions">
                <span>{{ formatDateTime(c.created_at) }}</span>
                <button v-if="canDelete(c)" type="button" class="ibtn danger" data-tip="Удалить" aria-label="Удалить комментарий" @click="handleDeleteComment(c)"><UiIcon name="trash" /></button>
              </span>
            </div>
            <p>{{ c.text }}</p>
          </div>

          <form v-if="isLoggedIn" class="comment-form stack-sm" @submit.prevent="handleComment">
            <label>Ваш комментарий
              <textarea v-model="text" rows="3" maxlength="3000" required></textarea>
            </label>
            <p class="error-text" role="alert">{{ commentError }}</p>
            <div class="row"><button class="btn primary" type="submit" :disabled="sending || !text.trim()">Отправить</button></div>
          </form>
          <p v-else class="notice">Чтобы оставить комментарий, <router-link :to="{ path: '/login', query: { redirect: route.fullPath } }">войдите</router-link>.</p>
        </section>
      </article>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon } from '../../components/index.js'
import MarkdownView from '../../components/MarkdownView.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { addComment, deleteComment, loadPost } from '../../../logic/actions/index.js'
import { useAuthStore } from '../../../logic/store/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'
import { formatDate, formatDateTime, initials } from './blogFormat.js'

const route = useRoute()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const auth = useAuthStore()
const userId = computed(() => auth.user?.user_id ?? null)

const post = ref(null)
const comments = ref([])
const error = ref('')
const text = ref('')
const sending = ref(false)
const commentError = ref('')
const isAuthor = computed(() => post.value && post.value.author_id === userId.value)

function canDelete(c) {
  return role.value === 'admin' || c.author_id === userId.value || isAuthor.value
}

async function load() {
  error.value = ''
  post.value = null
  try {
    const data = await loadPost(route.params.id)
    post.value = data.post
    comments.value = data.comments
    document.title = `${data.post.title} · Блог · SHAD`
  } catch (e) {
    error.value = e.message || 'Запись не найдена'
  }
}

async function handleComment() {
  commentError.value = ''
  sending.value = true
  try {
    comments.value = [...comments.value, await addComment(post.value.id, text.value.trim())]
    text.value = ''
  } catch (e) {
    commentError.value = e.message || 'Не удалось отправить комментарий'
  } finally {
    sending.value = false
  }
}

async function handleDeleteComment(c) {
  if (!(await askConfirm('Удалить комментарий?', 'Комментарий исчезнет без возможности восстановления.', { okText: 'Удалить', danger: true }))) return
  try {
    await deleteComment(c.id)
    comments.value = comments.value.filter((x) => x.id !== c.id)
  } catch (e) {
    toast(e.message || 'Не удалось удалить', 'error')
  }
}

watch(() => route.params.id, (id) => { if (id) load() }, { immediate: true })
</script>

<style scoped>
.post { max-width: 760px; margin: 0 auto; }
.post-title { font-size: 2rem; margin: 4px 0 12px; }
.post-meta { margin-bottom: 24px; }
.post-meta a { color: var(--text); }
.post-tags { margin-top: 20px; }
.pp .avatar.small { width: 28px; height: 28px; font-size: 12px; }
.comments h2 { font-size: 1.1rem; }
.comment-form { margin-top: 20px; }
.btn-ico { width: 15px; height: 15px; }
.pp .ibtn :deep(.ui-icon) { width: 16px; height: 16px; }
</style>
