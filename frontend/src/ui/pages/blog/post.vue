<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp blog-post">
      <div v-if="error" class="notice error" role="alert">
        {{ error }} <router-link to="/blog">К блогу</router-link>
      </div>
      <div v-else-if="!post" class="skeleton tall" aria-hidden="true"></div>
      <article v-else class="post">
        <router-link class="back" :to="authorLink">{{ post.owner ? '← На главную' : `← Блог: ${post.author_name}` }}</router-link>
        <h1 class="post-title">{{ post.title }}</h1>
        <div class="meta post-meta">
          <UserAvatar :src="post.author_avatar" :name="post.author_name" :size="28" />
          <router-link :to="authorLink">{{ post.author_name }}</router-link>
          <span>{{ post.status === 'published' ? formatDate(post.published_at) : 'Черновик — видите только вы' }}</span>
          <span v-if="post.status !== 'published'" class="badge draft">черновик</span>
          <router-link v-if="isAuthor" class="btn small ghost" :to="`/blog/manage/${post.id}`">
            <UiIcon name="edit" class="btn-ico" /> Изменить
          </router-link>
        </div>
        <MarkdownView :source="post.body" />
        <div v-if="post.tags.length" class="tags post-tags">
          <router-link v-for="t in post.tags" :key="t" class="tag" :to="{ path: post.owner ? '/' : '/blog', query: { tag: t } }">#{{ t }}</router-link>
        </div>
        <div v-if="post.owner && post.status === 'published'" class="post-like">
          <LikeButton :count="post.like_count" :liked="post.liked" :busy="liking" @toggle="toggleLike" />
        </div>

        <section v-if="post.status === 'published'" class="comments" aria-labelledby="comments-title">
          <h2 id="comments-title">Комментарии <span class="muted">{{ comments.length }}</span></h2>
          <p v-if="!comments.length" class="muted">Комментариев пока нет — будьте первым.</p>

          <div v-for="thread in threads" :key="thread.root.id" class="thread">
            <div v-for="c in [thread.root, ...thread.replies]" :key="c.id" class="comment" :class="{ reply: c.parent_id }">
              <UserAvatar :src="c.author_avatar" :name="c.author_name" :size="c.parent_id ? 26 : 32" />
              <div class="comment-body">
                <div class="comment-head">
                  <span><strong>{{ c.author_name }}</strong> <span v-if="c.author_id === post.author_id" class="badge">автор</span>
                    <span v-else-if="c.author_role === 'student'" class="muted"> · ученик</span>
                    <span v-else-if="c.author_role === 'tutor'" class="muted"> · репетитор</span></span>
                  <span class="row-actions">
                    <span class="muted small">{{ formatDateTime(c.created_at) }}</span>
                    <button v-if="canDelete(c)" type="button" class="ibtn danger" data-tip="Удалить" aria-label="Удалить комментарий" @click="handleDeleteComment(c)"><UiIcon name="trash" /></button>
                  </span>
                </div>
                <p class="comment-text">{{ c.text }}</p>
                <button v-if="canReply(c, thread)" type="button" class="more reply-btn" @click="startReply(c)">Ответить</button>
              </div>
            </div>
            <form v-if="replyTo && replyRoot === thread.root.id" class="comment-form reply-form stack-sm" @submit.prevent="sendReply">
              <label>Ответ для {{ replyTo.author_name }}
                <textarea ref="replyInput" v-model="replyText" rows="2" maxlength="3000" required @keydown.esc="cancelReply"></textarea>
              </label>
              <p v-if="replyError" class="error-text" role="alert">{{ replyError }}</p>
              <div class="row">
                <button class="btn primary" type="submit" :disabled="sending || !replyText.trim()">Ответить</button>
                <button class="btn ghost" type="button" @click="cancelReply">Отмена</button>
              </div>
            </form>
          </div>

          <p v-if="isAuthor" class="muted small comment-rule">Вы автор записи: можно ответить на каждый комментарий один раз.</p>
          <p v-else-if="myComment" class="muted small comment-rule">Вы уже оставили комментарий. Изменить его нельзя — удалите и напишите заново.</p>
          <form v-else class="comment-form stack-sm" @submit.prevent="handleComment">
            <label>Ваш комментарий
              <textarea v-model="text" rows="3" maxlength="3000" required></textarea>
            </label>
            <p v-if="commentError" class="error-text" role="alert">{{ commentError }}</p>
            <div class="row"><button class="btn primary" type="submit" :disabled="sending || !text.trim()">Отправить</button></div>
          </form>
        </section>
      </article>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon, UserAvatar } from '../../components/index.js'
import MarkdownView from '../../components/MarkdownView.vue'
import LikeButton from './LikeButton.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { addComment, deleteComment, likePost, loadPost } from '../../../logic/actions/index.js'
import { useAuthStore } from '../../../logic/store/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'
import { formatDate, formatDateTime, commentThreads } from './blogFormat.js'

const route = useRoute()
const router = useRouter()
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
const liking = ref(false)
const replyTo = ref(null)
const replyText = ref('')
const replyError = ref('')
const replyInput = ref(null)
// Записи владельца живут на главной, записи репетиторов — в их блогах.
const authorLink = computed(() => (post.value?.owner ? '/' : `/blog/authors/${post.value?.author_id}`))
const isAuthor = computed(() => post.value && post.value.author_id === userId.value)
const threads = computed(() => commentThreads(comments.value))
const replyRoot = computed(() => (replyTo.value ? replyTo.value.parent_id || replyTo.value.id : null))

// Свой комментарий верхнего уровня у читателя (один на запись).
const myComment = computed(() => comments.value.find((c) => !c.parent_id && c.author_id === userId.value) || null)
// Отвечает только автор записи — один раз на каждый чужой комментарий.
function canReply(c, thread) {
  return isAuthor.value && !c.parent_id && c.author_id !== userId.value && !thread.replies.length
}

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

async function toggleLike() {
  if (!isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  liking.value = true
  try {
    const res = await likePost(post.value.id)
    post.value = { ...post.value, liked: res.liked, like_count: res.like_count }
  } catch (e) {
    toast(e.message || 'Не удалось отметить запись', 'error')
  } finally {
    liking.value = false
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

async function startReply(c) {
  replyTo.value = c
  replyError.value = ''
  replyText.value = `${c.author_name.split(' ')[0]}, `
  await nextTick()
  const el = Array.isArray(replyInput.value) ? replyInput.value[0] : replyInput.value
  el?.focus()
}
function cancelReply() {
  replyTo.value = null
  replyText.value = ''
}
async function sendReply() {
  replyError.value = ''
  sending.value = true
  try {
    comments.value = [...comments.value, await addComment(post.value.id, replyText.value.trim(), replyTo.value.id)]
    cancelReply()
  } catch (e) {
    replyError.value = e.message || 'Не удалось отправить ответ'
  } finally {
    sending.value = false
  }
}

async function handleDeleteComment(c) {
  const hasReplies = !c.parent_id && comments.value.some((x) => x.parent_id === c.id)
  const message = hasReplies ? 'Комментарий и ответы на него исчезнут без возможности восстановления.' : 'Комментарий исчезнет без возможности восстановления.'
  if (!(await askConfirm('Удалить комментарий?', message, { okText: 'Удалить', danger: true }))) return
  try {
    await deleteComment(c.id)
    comments.value = comments.value.filter((x) => x.id !== c.id && x.parent_id !== c.id)
  } catch (e) {
    toast(e.message || 'Не удалось удалить', 'error')
  }
}

watch(() => route.params.id, (id) => { if (id) load() }, { immediate: true })
</script>

<style scoped>
.post { max-width: 760px; margin: 0 auto; }
.post-title { font-size: 2rem; margin: 4px 0 12px; }
.post-meta { margin-bottom: 24px; align-items: center; }
.post-meta a { color: var(--text); }
.post-tags { margin-top: 20px; }
.post-like { margin-top: 18px; }
.comments h2 { font-size: 1.1rem; }
.thread { display: grid; gap: 0; border-bottom: 1px solid var(--line); padding: 6px 0; }
.thread:last-of-type { border-bottom: 0; }
.comment { display: flex; gap: 12px; padding: 10px 0; border: 0; }
.comment.reply { margin-left: 44px; padding-top: 4px; }
.comment-body { flex: 1; min-width: 0; }
.comment-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.comment-text { margin: 4px 0 2px; white-space: pre-wrap; overflow-wrap: anywhere; }
.reply-btn { font-size: 13px; }
.reply-form { margin: 4px 0 10px 44px; }
.comment-form { margin-top: 20px; }
.comment-rule { margin-top: 16px; }
.btn-ico { width: 15px; height: 15px; }
.pp .ibtn :deep(.ui-icon) { width: 16px; height: 16px; }
@media (max-width: 600px) { .comment.reply, .reply-form { margin-left: 20px; } }
</style>
