<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp blog-page">
      <div class="page-grid">
        <div class="page-main">
          <div class="page-head">
            <router-link v-if="authorId" class="back" :to="{ path: '/blog', query: keepQuery({ author: undefined }) }">← Все блоги</router-link>
            <div v-if="author" class="author-head">
              <UserAvatar :src="author.avatar_url" :name="author.full_name" :size="48" />
              <h1>Блог: {{ author.full_name }}</h1>
            </div>
            <h1 v-else>Блог репетиторов</h1>
            <p class="lead">{{ author ? (author.about || 'Заметки, материалы и советы репетитора.') : 'Заметки, материалы и советы репетиторов платформы.' }}</p>
          </div>

          <!-- Поиск и фильтры: каждый работает сам по себе и вместе с остальными -->
          <form class="search-form" role="search" @submit.prevent="applySearch">
            <input v-model="searchText" type="search" class="grow" placeholder="Поиск по названию записи" aria-label="Поиск по названию записи" />
            <select v-model="authorChoice" aria-label="Автор" @change="setAuthor(authorChoice)">
              <option value="">Все авторы</option>
              <option v-for="a in authors" :key="a.id" :value="String(a.id)">{{ a.full_name }}</option>
            </select>
            <button type="submit" class="btn primary">Найти</button>
          </form>

          <div v-if="hasFilters" class="active-filters" aria-label="Активные фильтры">
            <span class="muted small">Показаны:</span>
            <button v-if="author" type="button" class="chip on" :aria-label="`Убрать фильтр по автору ${author.full_name}`" @click="setAuthor('')">{{ author.full_name }} ✕</button>
            <button v-if="tag" type="button" class="chip on" :aria-label="`Убрать тег ${tag}`" @click="setTag(null)">#{{ tag }} ✕</button>
            <button v-if="query" type="button" class="chip on" :aria-label="`Убрать поиск ${query}`" @click="setQuery('')">«{{ query }}» ✕</button>
            <button type="button" class="more" @click="resetAll">Сбросить всё</button>
          </div>

          <div v-if="error" class="notice error" role="alert">{{ error }}</div>
          <div v-else-if="loading && !posts.length" class="sk-stack" aria-hidden="true"><div class="skeleton"></div><div class="skeleton"></div></div>
          <div v-else-if="!posts.length" class="empty">
            <p class="muted">{{ hasFilters ? 'По этим условиям записей нет.' : 'Записей пока нет.' }}</p>
            <button v-if="hasFilters" type="button" class="btn ghost" @click="resetAll">Сбросить фильтры</button>
          </div>
          <div v-else class="feed">
            <p class="muted small found">{{ foundText }}</p>
            <article v-for="post in posts" :key="post.id" class="feed-card">
              <div class="feed-head">
                <UserAvatar :src="post.author_avatar" :name="post.author_name" :size="36" />
                <div class="feed-who">
                  <button type="button" class="author-link" @click="setAuthor(String(post.author_id))"><strong>{{ post.author_name }}</strong></button>
                  <div class="meta"><span>{{ formatDate(post.published_at) }}</span><span v-if="post.pinned && authorId" class="pin-label">Закреплено</span></div>
                </div>
              </div>
              <h2 class="feed-title"><router-link :to="`/blog/posts/${post.id}`">{{ post.title }}</router-link></h2>
              <MarkdownView :source="post.body" :clamp="!expanded.has(post.id)" @cut="(cut) => setCut(post.id, cut)" />
              <button v-if="cutPosts.has(post.id) && !expanded.has(post.id)" type="button" class="more" @click="expanded.add(post.id)">Показать полностью</button>
              <div v-if="post.tags.length" class="tags">
                <button v-for="t in post.tags" :key="t" type="button" class="tag" :class="{ active: t === tag }" :aria-pressed="t === tag" @click="setTag(t === tag ? null : t)">#{{ t }}</button>
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
          <section v-if="role === 'tutor'" class="side-card">
            <h2>Мой блог</h2>
            <p>Пишите заметки и материалы для учеников. Черновики видите только вы.</p>
            <router-link class="btn primary" to="/blog/manage/new">Новая запись</router-link>
            <router-link class="btn ghost" to="/blog/manage">Мои записи</router-link>
          </section>
          <section v-if="tagChoices.length" class="side-card">
            <h2>Темы</h2>
            <div class="tags">
              <button v-for="t in tagChoices" :key="t.tag" type="button" class="tag" :class="{ active: t.tag === tag }" :aria-pressed="t.tag === tag" @click="setTag(t.tag === tag ? null : t.tag)">
                #{{ t.tag }} <small v-if="t.count">{{ t.count }}</small>
              </button>
            </div>
          </section>
          <section class="side-card">
            <h2>Авторы</h2>
            <p v-if="!authors.length" class="muted">Пока никто не публиковал записи.</p>
            <ul v-else class="authors">
              <li v-for="a in authors" :key="a.id">
                <router-link :to="{ path: `/blog/authors/${a.id}`, query: keepQuery() }" :aria-current="String(a.id) === String(authorId) ? 'page' : null">
                  <UserAvatar :src="a.avatar_url" :name="a.full_name" :size="28" />
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
import { UiIcon, UserAvatar } from '../../components/index.js'
import MarkdownView from '../../components/MarkdownView.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { loadAuthor, loadAuthors, loadFeed } from '../../../logic/actions/index.js'
import { commentsWord, formatDate } from './blogFormat.js'

const PAGE = 10
const route = useRoute()
const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()

const authorId = computed(() => route.params.authorId || null)
const tag = computed(() => (typeof route.query.tag === 'string' && route.query.tag ? route.query.tag : null))
const query = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim() : ''))
const hasFilters = computed(() => Boolean(authorId.value || tag.value || query.value))
const posts = ref([])
const total = ref(0)
const author = ref(null)
const authors = ref([])
const seenTags = ref([])
const loading = ref(false)
const error = ref('')
const expanded = reactive(new Set())
const cutPosts = reactive(new Set())
const searchText = ref(query.value)
const authorChoice = ref(authorId.value ? String(authorId.value) : '')

// Темы: у выбранного автора — его теги с числом записей, иначе — теги из уже показанных записей.
const tagChoices = computed(() => (author.value?.tags?.length ? author.value.tags : seenTags.value.map((t) => ({ tag: t, count: 0 }))))
const foundText = computed(() => (hasFilters.value ? `Найдено записей: ${total.value}` : ''))

function setCut(id, cut) { if (cut) cutPosts.add(id); else cutPosts.delete(id) }

// Текущие фильтры в адресе: ссылками можно делиться, «Назад» возвращает прежний выбор.
function keepQuery(patch = {}) {
  const next = { tag: tag.value || undefined, q: query.value || undefined, ...patch }
  delete next.author
  return Object.fromEntries(Object.entries(next).filter(([, v]) => v))
}
function go(path, patch) { router.push({ path, query: keepQuery(patch) }) }
function setTag(value) { go(route.path, { tag: value || undefined }) }
function setQuery(value) { go(route.path, { q: value || undefined }) }
function setAuthor(id) { go(id ? `/blog/authors/${id}` : '/blog') }
function applySearch() { setQuery(searchText.value.trim()) }
function resetAll() { searchText.value = ''; router.push({ path: '/blog' }) }

async function load(reset = true) {
  loading.value = true
  error.value = ''
  try {
    const data = await loadFeed({
      author_id: authorId.value || undefined, tag: tag.value || undefined, q: query.value || undefined,
      limit: PAGE, offset: reset ? 0 : posts.value.length,
    })
    posts.value = reset ? data.items : [...posts.value, ...data.items]
    total.value = data.total
    const seen = new Set(seenTags.value)
    for (const p of data.items) for (const t of p.tags) seen.add(t)
    seenTags.value = [...seen]
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить записи'
  } finally {
    loading.value = false
  }
}

async function loadSide() {
  author.value = null
  const [list, one] = await Promise.allSettled([loadAuthors(), authorId.value ? loadAuthor(authorId.value) : Promise.resolve(null)])
  if (list.status === 'fulfilled') authors.value = list.value.items
  if (one.status === 'fulfilled') author.value = one.value
  else if (authorId.value) error.value = one.reason?.message || 'Блог не найден'
  document.title = `${author.value ? `Блог: ${author.value.full_name}` : 'Блог репетиторов'} · SHAD`
}

watch(() => route.fullPath, () => {
  if (route.name !== 'blog' && route.name !== 'blog-author') return
  searchText.value = query.value
  authorChoice.value = authorId.value ? String(authorId.value) : ''
  expanded.clear()
  cutPosts.clear()
  load()
}, { immediate: true })
watch(authorId, loadSide, { immediate: true })
</script>

<style scoped>
.author-head { display: flex; align-items: center; gap: 14px; }
.author-head h1 { margin: 0; }
.search-form select { width: auto; max-width: 200px; height: 34px; border: 0; background: transparent; }
.search-form input { border: 0; background: transparent; box-shadow: none; padding-left: 0; }
.search-form input:focus { box-shadow: none; }
.active-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: -12px 0 18px; }
.active-filters .chip { cursor: pointer; font-size: 13px; touch-action: auto; }
.found { margin: 0 0 4px; }
.author-link { border: 0; background: none; padding: 0; color: var(--text); cursor: pointer; font: inherit; }
.author-link:hover { color: var(--accent); }
.authors { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.authors a { display: flex; align-items: center; gap: 10px; padding: 6px 8px; margin: 0 -8px; border-radius: 8px; color: var(--text); }
.authors a:hover, .authors a[aria-current='page'] { background: var(--surface-2); text-decoration: none; }
.feed-who a { color: var(--text); }
.meta-ico { width: 16px; height: 16px; display: inline-block; vertical-align: -3px; }
.load-more { justify-self: center; }
@media (max-width: 600px) {
  .search-form { flex-wrap: wrap; }
  .search-form select { max-width: none; flex: 1 1 100%; order: 3; }
}
</style>
