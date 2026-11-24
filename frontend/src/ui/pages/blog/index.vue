<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp blog-page">
      <div class="page-grid">
        <div class="page-main">
          <div class="page-head">
            <router-link v-if="authorId" class="back" to="/blog">← Все блоги</router-link>
            <h1>{{ author ? `Блог: ${author.full_name}` : 'Блог репетиторов' }}</h1>
            <p class="lead">{{ author ? (author.about || 'Заметки, материалы и советы репетитора.') : 'Заметки, материалы и советы репетиторов платформы.' }}</p>
          </div>

          <div v-if="tag" class="notice filter-note">
            <span>Записи с тегом <span class="tag static">#{{ tag }}</span></span>
            <button type="button" class="more" @click="setTag(null)">Сбросить</button>
          </div>

          <div v-if="error" class="notice error" role="alert">{{ error }}</div>
          <div v-else-if="loading && !posts.length" class="sk-stack" aria-hidden="true"><div class="skeleton"></div><div class="skeleton"></div></div>
          <div v-else-if="!posts.length" class="empty">
            <p class="muted">{{ tag ? `Записей с тегом #${tag} нет.` : 'Записей пока нет.' }}</p>
            <button v-if="tag" type="button" class="btn ghost" @click="setTag(null)">Показать все записи</button>
          </div>
          <div v-else class="feed">
            <article v-for="post in posts" :key="post.id" class="feed-card">
              <div class="feed-head">
                <span class="avatar" aria-hidden="true">{{ initials(post.author_name) }}</span>
                <div class="feed-who">
                  <router-link :to="`/blog/authors/${post.author_id}`"><strong>{{ post.author_name }}</strong></router-link>
                  <div class="meta"><span>{{ formatDate(post.published_at) }}</span><span v-if="post.pinned && authorId" class="pin-label">Закреплено</span></div>
                </div>
              </div>
              <h2 class="feed-title"><router-link :to="`/blog/posts/${post.id}`">{{ post.title }}</router-link></h2>
              <MarkdownView :source="post.body" :clamp="!expanded.has(post.id)" @cut="(cut) => setCut(post.id, cut)" />
              <button v-if="cutPosts.has(post.id) && !expanded.has(post.id)" type="button" class="more" @click="expand(post.id)">Показать полностью</button>
              <div v-if="post.tags.length" class="tags">
                <button v-for="t in post.tags" :key="t" type="button" class="tag" :class="{ active: t === tag }" @click="setTag(t)">#{{ t }}</button>
              </div>
              <div class="feed-actions">
                <span class="meta"><UiIcon name="chat" class="meta-ico" /> {{ post.comment_count }} {{ commentsWord(post.comment_count) }}</span>
                <router-link class="feed-open" :to="`/blog/posts/${post.id}`">Открыть →</router-link>
              </div>
            </article>
            <button v-if="posts.length < total" type="button" class="btn ghost load-more" :disabled="loading" @click="loadMore">Показать ещё</button>
          </div>
        </div>

        <aside class="page-side">
          <section v-if="role === 'tutor'" class="side-card">
            <h2>Мой блог</h2>
            <p>Пишите заметки и материалы для учеников. Черновики видите только вы.</p>
            <router-link class="btn primary" to="/blog/manage/new">Новая запись</router-link>
            <router-link class="btn ghost" to="/blog/manage">Мои записи</router-link>
          </section>
          <section v-if="author && author.tags.length" class="side-card">
            <h2>Темы</h2>
            <div class="tags">
              <button v-for="t in author.tags" :key="t.tag" type="button" class="tag" :class="{ active: t.tag === tag }" @click="setTag(t.tag)">
                #{{ t.tag }} <small>{{ t.count }}</small>
              </button>
            </div>
          </section>
          <section class="side-card">
            <h2>Авторы</h2>
            <p v-if="!authors.length" class="muted">Пока никто не публиковал записи.</p>
            <ul v-else class="authors">
              <li v-for="a in authors" :key="a.id">
                <router-link :to="`/blog/authors/${a.id}`" :aria-current="String(a.id) === String(authorId) ? 'page' : null">
                  <span class="avatar small" aria-hidden="true">{{ initials(a.full_name) }}</span>
                  <span class="grow">{{ a.full_name }}</span>
                  <small class="muted">{{ a.post_count }}</small>
                </router-link>
              </li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon } from '../../components/index.js'
import MarkdownView from '../../components/MarkdownView.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { loadAuthor, loadAuthors, loadFeed } from '../../../logic/actions/index.js'
import { commentsWord, formatDate, initials } from './blogFormat.js'

const PAGE = 10
const route = useRoute()
const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()

const authorId = computed(() => route.params.authorId || null)
const tag = computed(() => (typeof route.query.tag === 'string' ? route.query.tag : null))
const posts = ref([])
const total = ref(0)
const author = ref(null)
const authors = ref([])
const loading = ref(false)
const error = ref('')
const expanded = reactive(new Set())
const cutPosts = reactive(new Set())

function setCut(id, cut) { if (cut) cutPosts.add(id); else cutPosts.delete(id) }
function expand(id) { expanded.add(id) }
function setTag(value) { router.push({ path: route.path, query: value ? { tag: value } : {} }) }

async function load(reset = true) {
  loading.value = true
  error.value = ''
  try {
    const data = await loadFeed({ author_id: authorId.value || undefined, tag: tag.value || undefined, limit: PAGE, offset: reset ? 0 : posts.value.length })
    posts.value = reset ? data.items : [...posts.value, ...data.items]
    total.value = data.total
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить записи'
  } finally {
    loading.value = false
  }
}
const loadMore = () => load(false)

async function loadSide() {
  author.value = null
  // Список авторов и шапка блога загружаются независимо: ошибка одного не скрывает другое.
  const [list, one] = await Promise.allSettled([loadAuthors(), authorId.value ? loadAuthor(authorId.value) : Promise.resolve(null)])
  if (list.status === 'fulfilled') authors.value = list.value.items
  if (one.status === 'fulfilled') author.value = one.value
  else if (authorId.value) error.value = one.reason?.message || 'Блог не найден'
  document.title = `${author.value ? `Блог: ${author.value.full_name}` : 'Блог репетиторов'} · SHAD`
}

watch(() => route.fullPath, () => {
  if (route.name !== 'blog' && route.name !== 'blog-author') return
  expanded.clear()
  cutPosts.clear()
  load()
}, { immediate: true })
watch(authorId, loadSide, { immediate: true })
</script>

<style scoped>
.filter-note { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }
.authors { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.authors a { display: flex; align-items: center; gap: 10px; padding: 6px 8px; margin: 0 -8px; border-radius: 8px; color: var(--text); }
.authors a:hover, .authors a[aria-current='page'] { background: var(--surface-2); text-decoration: none; }
.pp .avatar.small { width: 28px; height: 28px; font-size: 12px; }
.feed-who a { color: var(--text); }
.meta-ico { width: 16px; height: 16px; display: inline-block; vertical-align: -3px; }
.load-more { justify-self: center; }
</style>
