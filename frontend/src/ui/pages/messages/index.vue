<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp messages-page" :class="{ 'has-open': partnerId }">
      <aside class="dialogs" aria-label="Диалоги">
        <h1>Сообщения</h1>
        <p v-if="!connected" class="muted small">Подключаемся… сообщения придут, как только появится связь.</p>
        <div v-if="error" class="notice error" role="alert">{{ error }}</div>
        <div v-else-if="loading && !dialogs.length" class="skeleton" aria-hidden="true"></div>
        <p v-else-if="!dialogs.length" class="muted">
          {{ role === 'tutor' ? 'Диалоги появятся, когда у вас будут ученики.' : 'Диалоги появятся, когда вы свяжетесь с репетитором.' }}
        </p>
        <ul v-else class="dialog-list">
          <li v-for="d in dialogs" :key="d.partner_id">
            <router-link :to="`/messages/${d.partner_id}`" class="dialog" :aria-current="d.partner_id === partnerId ? 'page' : null">
              <UserAvatar :src="d.partner_avatar" :name="d.partner_name" :size="38" />
              <span class="dialog-copy">
                <span class="dialog-top"><strong>{{ d.partner_name }}</strong><small class="muted">{{ shortTime(d.last_at) }}</small></span>
                <span class="dialog-last muted">
                  <template v-if="d.last_text">{{ d.last_from_me ? 'Вы: ' : '' }}{{ d.last_text }}</template>
                  <template v-else>{{ d.partner_role === 'tutor' ? 'Репетитор' : 'Ученик' }} · сообщений нет</template>
                </span>
              </span>
              <span v-if="d.unread" class="unread" :aria-label="`Непрочитанных: ${d.unread}`">{{ d.unread }}</span>
            </router-link>
          </li>
        </ul>
      </aside>

      <section class="conversation" :aria-label="current ? `Переписка с ${current.partner_name}` : 'Переписка'">
        <template v-if="current">
          <header class="conv-head">
            <router-link class="back-link" to="/messages" aria-label="К списку диалогов">←</router-link>
            <UserAvatar :src="current.partner_avatar" :name="current.partner_name" :size="32" />
            <div><strong>{{ current.partner_name }}</strong><div class="muted small">{{ current.partner_role === 'tutor' ? 'Репетитор' : 'Ученик' }}</div></div>
          </header>
          <ChatThread :partner-id="current.partner_id" :partner-name="current.partner_name" :can-write="current.can_write" />
        </template>
        <p v-else-if="partnerId && !loading" class="muted center">Диалог не найден.</p>
        <p v-else class="muted center">Выберите диалог слева.</p>
      </section>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { UserAvatar } from '../../components/index.js'
import { useLogout, useUser } from '../../composables/index.js'
import { loadChatDialogs } from '../../../logic/actions/index.js'
import { userNowIso } from '../../../logic/utils/index.js'
import { useChatStore } from '../../../logic/store/index.js'
import ChatThread from './ChatThread.vue'

const route = useRoute()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const store = useChatStore()
const loading = ref(false)
const error = ref('')

const dialogs = computed(() => store.dialogs)
const connected = computed(() => store.connected)
const partnerId = computed(() => (route.params.partnerId ? Number(route.params.partnerId) : null))
const current = computed(() => dialogs.value.find((d) => d.partner_id === partnerId.value) || null)

function shortTime(iso) {
  if (!iso) return ''
  const s = String(iso)
  const today = userNowIso().slice(0, 10) // «сегодня» — в поясе пользователя, как и время сообщений
  return s.slice(0, 10) === today ? s.slice(11, 16) : `${s.slice(8, 10)}.${s.slice(5, 7)}`
}

onMounted(async () => {
  document.title = 'Сообщения · SHAD'
  loading.value = true
  try {
    await loadChatDialogs()
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить диалоги'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.messages-page { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; height: calc(100dvh - var(--shell-h, 64px) - 120px); min-height: 460px; }
.dialogs { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
.dialogs h1 { font-size: 24px; margin: 0 0 6px; }
.dialog-list { list-style: none; margin: 0; padding: 0; overflow-y: auto; display: grid; gap: 2px; align-content: start; }
.dialog { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 12px; color: var(--text); }
.dialog:hover { background: var(--surface); text-decoration: none; }
.dialog[aria-current='page'] { background: var(--accent-soft); }
.dialog-copy { display: grid; gap: 2px; min-width: 0; flex: 1; }
.dialog-top { display: flex; justify-content: space-between; gap: 8px; }
.dialog-last { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.unread { min-width: 20px; height: 20px; padding: 0 6px; border-radius: 999px; background: var(--accent); color: var(--accent-ink); font-size: 11.5px; font-weight: 600; display: inline-grid; place-items: center; }
.conversation { display: flex; flex-direction: column; min-height: 0; border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--surface); padding: 12px 16px; }
.conv-head { display: flex; align-items: center; gap: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--line); }
.back-link { display: none; font-size: 20px; color: var(--text); padding: 0 6px; }
.center { margin: auto; }
@media (max-width: 800px) {
  .messages-page { grid-template-columns: minmax(0, 1fr); height: calc(100dvh - var(--shell-h, 104px) - 80px); }
  .messages-page.has-open .dialogs { display: none; }
  .messages-page:not(.has-open) .conversation { display: none; }
  .back-link { display: inline; }
}
</style>
