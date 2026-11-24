<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp blog-manage">
      <div class="toolbar">
        <div>
          <h1>Мой блог</h1>
          <p class="lead">Записи для учеников и гостей сайта. Черновики видите только вы.</p>
        </div>
        <div class="row">
          <router-link v-if="userId" class="btn ghost" :to="`/blog/authors/${userId}`">Открыть блог</router-link>
          <router-link class="btn primary" to="/blog/manage/new"><UiIcon name="plus" class="btn-ico" /> Новая запись</router-link>
        </div>
      </div>

      <div v-if="error" class="notice error" role="alert">{{ error }}</div>
      <div v-else-if="loading" class="skeleton" aria-hidden="true"></div>
      <div v-else-if="!posts.length" class="empty">
        <p class="muted">Записей пока нет. Расскажите ученикам о подходе к занятиям или поделитесь материалами.</p>
        <router-link class="btn primary" to="/blog/manage/new">Написать первую запись</router-link>
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead><tr><th>Запись</th><th>Статус</th><th>Обновлена</th><th>Комментарии</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in posts" :key="p.id">
              <td>
                <router-link :to="`/blog/manage/${p.id}`" class="row-title">{{ p.title }}</router-link>
                <span v-if="p.pinned" class="pin-label">закреплена</span>
                <div v-if="p.tags.length" class="muted small">{{ p.tags.map((t) => '#' + t).join(' ') }}</div>
              </td>
              <td><span class="badge" :class="p.status === 'published' ? 'ok' : 'draft'">{{ p.status === 'published' ? 'опубликована' : 'черновик' }}</span></td>
              <td class="nowrap">{{ formatDateTime(p.updated_at) }}</td>
              <td>{{ p.comment_count }}</td>
              <td>
                <span class="row-actions">
                  <router-link class="ibtn" :to="`/blog/posts/${p.id}`" data-tip="Просмотр" aria-label="Просмотр записи"><UiIcon name="open" /></router-link>
                  <router-link class="ibtn" :to="`/blog/manage/${p.id}`" data-tip="Изменить" aria-label="Изменить запись"><UiIcon name="edit" /></router-link>
                  <button type="button" class="ibtn danger" data-tip="Удалить" :aria-label="`Удалить запись ${p.title}`" @click="handleDelete(p)"><UiIcon name="trash" /></button>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UiIcon } from '../../components/index.js'
import { useLogout, useUser } from '../../composables/index.js'
import { deletePost, loadMyPosts } from '../../../logic/actions/index.js'
import { useAuthStore } from '../../../logic/store/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'
import { formatDateTime } from './blogFormat.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const auth = useAuthStore()
const userId = computed(() => auth.user?.user_id ?? null)
const posts = ref([])
const loading = ref(true)
const error = ref('')

async function handleDelete(post) {
  const ok = await askConfirm(`Удалить запись «${post.title}»?`, 'Запись и комментарии к ней будут удалены безвозвратно.', { okText: 'Удалить', danger: true })
  if (!ok) return
  try {
    await deletePost(post.id)
    posts.value = posts.value.filter((p) => p.id !== post.id)
    toast('Запись удалена', 'ok')
  } catch (e) {
    toast(e.message || 'Не удалось удалить', 'error')
  }
}

onMounted(async () => {
  document.title = 'Мой блог · SHAD'
  try {
    posts.value = (await loadMyPosts()).items
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить записи'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.row-title { color: var(--text); font-weight: 500; margin-right: 8px; }
.btn-ico { width: 16px; height: 16px; }
.small { font-size: 13px; }
.nowrap { white-space: nowrap; }
.pp .ibtn :deep(.ui-icon) { width: 16px; height: 16px; }
</style>
