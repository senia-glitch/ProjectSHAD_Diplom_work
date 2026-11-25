<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp home-page">
      <div class="page-grid">
        <div class="page-main">
          <div class="page-head">
            <p class="eyebrow">SHAD Tutoring</p>
            <h1>{{ isLoggedIn && userName ? `Здравствуйте, ${userName}` : 'Блог платформы' }}</h1>
            <p class="lead">Новости, заметки и объявления от команды платформы.</p>
          </div>

          <div v-if="tag" class="notice filter-note">
            <span>Записи с тегом <span class="tag static">#{{ tag }}</span></span>
            <button type="button" class="more" @click="setTag(null)">Сбросить</button>
          </div>

          <div v-if="error" class="notice error" role="alert">{{ error }}</div>
          <div v-else-if="loading && !posts.length" class="sk-stack" aria-hidden="true"><div class="skeleton"></div><div class="skeleton"></div></div>
          <div v-else-if="!posts.length" class="empty">
            <p class="muted">{{ tag ? `Записей с тегом #${tag} нет.` : 'Записей пока нет.' }}</p>
            <router-link v-if="role === 'admin' && !tag" class="btn primary" to="/blog/manage/new">Написать первую запись</router-link>
            <button v-else-if="tag" type="button" class="btn ghost" @click="setTag(null)">Показать все записи</button>
          </div>
          <div v-else class="feed">
            <article v-for="post in posts" :key="post.id" class="feed-card">
              <div class="feed-head">
                <span class="avatar" aria-hidden="true">{{ initials(post.author_name) }}</span>
                <div class="feed-who">
                  <strong>{{ post.author_name }}</strong>
                  <div class="meta"><span>{{ formatDate(post.published_at) }}</span><span v-if="post.pinned" class="pin-label">Закреплено</span></div>
                </div>
              </div>
              <h2 class="feed-title"><router-link :to="`/blog/posts/${post.id}`">{{ post.title }}</router-link></h2>
              <MarkdownView :source="post.body" :clamp="!expanded.has(post.id)" @cut="(cut) => setCut(post.id, cut)" />
              <button v-if="cutPosts.has(post.id) && !expanded.has(post.id)" type="button" class="more" @click="expanded.add(post.id)">Показать полностью</button>
              <div v-if="post.tags.length" class="tags">
                <button v-for="t in post.tags" :key="t" type="button" class="tag" :class="{ active: t === tag }" @click="setTag(t)">#{{ t }}</button>
              </div>
              <div class="feed-actions">
                <span class="meta"><UiIcon name="chat" class="meta-ico" /> {{ post.comment_count }} {{ commentsWord(post.comment_count) }}</span>
                <router-link class="feed-open" :to="`/blog/posts/${post.id}`">Открыть →</router-link>
              </div>
            </article>
            <button v-if="posts.length < total" type="button" class="btn ghost load-more" :disabled="loading" @click="load(false)">Показать ещё</button>
          </div>
        </div>

        <aside class="page-side">
          <section v-if="!isLoggedIn" class="side-card">
            <h2>Расписание и занятия</h2>
            <p>Запись на уроки, тесты, доски и связь с репетитором — в одном кабинете.</p>
            <router-link class="btn primary" to="/login">Войти</router-link>
            <router-link class="btn ghost" to="/register">Создать аккаунт</router-link>
          </section>
          <section v-else-if="role === 'admin'" class="side-card">
            <h2>Блог владельца</h2>
            <p>Записи из раздела «Мой блог» публикуются здесь для всех посетителей.</p>
            <router-link class="btn primary" to="/blog/manage/new">Новая запись</router-link>
            <router-link class="btn ghost" to="/blog/manage">Мои записи</router-link>
          </section>
          <section v-if="tags.length" class="side-card">
            <h2>Темы</h2>
            <div class="tags">
              <button v-for="t in tags" :key="t" type="button" class="tag" :class="{ active: t === tag }" @click="setTag(t)">#{{ t }}</button>
            </div>
          </section>
          <section class="side-card">
            <h2>Блоги репетиторов</h2>
            <p>Материалы и советы преподавателей платформы.</p>
            <router-link class="btn ghost" to="/blog">Читать</router-link>
          </section>
        </aside>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
// Главная: блог владельца платформы для всех посетителей (закреплённые записи сверху).
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon } from '../../components/index.js'
import MarkdownView from '../../components/MarkdownView.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { loadFeed } from '../../../logic/actions/index.js'
import { commentsWord, formatDate, initials } from '../blog/blogFormat.js'

const PAGE = 10
const route = useRoute()
const router = useRouter()
const { role, isLoggedIn, userName } = useUser()
const { handleLogout } = useLogout()

const tag = computed(() => (typeof route.query.tag === 'string' ? route.query.tag : null))
const posts = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const expanded = reactive(new Set())
const cutPosts = reactive(new Set())
const allTags = ref([])
const tags = computed(() => allTags.value)

function setCut(id, cut) { if (cut) cutPosts.add(id); else cutPosts.delete(id) }
function setTag(value) { router.push({ path: '/', query: value ? { tag: value } : {} }) }

async function load(reset = true) {
  loading.value = true
  error.value = ''
  try {
    const data = await loadFeed({ owner: true, tag: tag.value || undefined, limit: PAGE, offset: reset ? 0 : posts.value.length })
    posts.value = reset ? data.items : [...posts.value, ...data.items]
    total.value = data.total
    if (!tag.value) {
      const seen = new Set(allTags.value)
      for (const p of posts.value) for (const t of p.tags) seen.add(t)
      allTags.value = [...seen]
    }
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить записи'
  } finally {
    loading.value = false
  }
}

watch(() => route.fullPath, () => {
  if (route.name !== 'home') return
  expanded.clear()
  cutPosts.clear()
  load()
}, { immediate: true })

document.title = 'SHAD Tutoring'
</script>

<style scoped>
.eyebrow { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; font-weight: 600; color: var(--accent); margin: 0 0 8px; }
.filter-note { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }
</style>
