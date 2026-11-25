<template>
  <div class="board-chat">
    <p v-if="!dialogs.length" class="muted small hint">
      Здесь появятся личные диалоги с участниками этой доски, с которыми у вас есть связь.
    </p>
    <template v-else>
      <div class="partners" role="tablist" aria-label="Собеседники на доске">
        <button
          v-for="d in dialogs"
          :key="d.partner_id"
          type="button"
          role="tab"
          class="partner"
          :class="{ active: d.partner_id === selectedId }"
          :aria-selected="d.partner_id === selectedId"
          @click="selectedId = d.partner_id"
        >
          <UserAvatar :src="d.partner_avatar" :name="d.partner_name" :size="22" />
          <span>{{ d.partner_name }}</span>
          <span v-if="unreadOf(d) && d.partner_id !== selectedId" class="unread">{{ unreadOf(d) }}</span>
        </button>
      </div>
      <!-- Переписка открыта только при видимой панели: иначе входящие считались бы прочитанными -->
      <ChatThread v-if="selected && panelOpen" :key="selected.partner_id" compact :partner-id="selected.partner_id" :partner-name="selected.partner_name" />
    </template>
  </div>
</template>

<script setup>
// Панель чата доски: личные диалоги с теми, кто сейчас на доске и связан со мной.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { UserAvatar } from '../../components/index.js'
import { loadBoardChatDialogs, onChatEvent } from '../../../logic/actions/index.js'
import { useChatStore } from '../../../logic/store/index.js'
import ChatThread from '../messages/ChatThread.vue'

const props = defineProps({ boardId: { type: String, required: true } })
const store = useChatStore()
const dialogs = ref([])
const selectedId = ref(null)
const extraUnread = ref({}) // входящие после загрузки списка, пока диалог не открыт
const selected = computed(() => dialogs.value.find((d) => d.partner_id === selectedId.value) || null)
const unreadOf = (d) => (d.unread || 0) + (extraUnread.value[d.partner_id] || 0)
const panelOpen = ref(false)
let timer = 0
let observer = null

// Панель чата доски открывает и закрывает код доски (атрибут hidden у #chat).
function watchPanel() {
  const aside = document.getElementById('chat')
  if (!aside) return
  const sync = () => {
    const open = !aside.hidden
    if (open && !panelOpen.value) refresh()
    panelOpen.value = open
  }
  sync()
  observer = new MutationObserver(sync)
  observer.observe(aside, { attributes: true, attributeFilter: ['hidden'] })
}

async function refresh() {
  try {
    dialogs.value = await loadBoardChatDialogs(props.boardId)
    extraUnread.value = {}
    if (!dialogs.value.some((d) => d.partner_id === selectedId.value)) selectedId.value = dialogs.value[0]?.partner_id ?? null
  } catch {
    // Панель необязательна: при ошибке остаётся прежний список.
  }
}

// Счётчик на кнопке «Чат» доски — непрочитанные в диалогах с участниками доски.
const totalUnread = computed(() => dialogs.value.reduce((n, d) => n + (panelOpen.value && d.partner_id === selectedId.value ? 0 : unreadOf(d)), 0))
watch(totalUnread, (n) => {
  const badge = document.getElementById('chat-badge')
  if (!badge) return
  badge.textContent = n > 9 ? '9+' : String(n)
  badge.hidden = n === 0
}, { immediate: true })

const off = onChatEvent((msg) => {
  if (msg.t !== 'message') return
  const m = msg.message
  const sender = m.sender_id
  if (dialogs.value.some((d) => d.partner_id === sender) && sender !== store.openPartner) {
    extraUnread.value = { ...extraUnread.value, [sender]: (extraUnread.value[sender] || 0) + 1 }
  }
})

onMounted(() => {
  watchPanel()
  refresh()
  timer = setInterval(refresh, 15000)
  window.addEventListener('board-peers', refresh)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  observer?.disconnect()
  window.removeEventListener('board-peers', refresh)
  off()
})
</script>

<style scoped>
.board-chat { display: flex; flex-direction: column; min-height: 0; flex: 1; gap: 8px; }
.hint { margin: 12px 4px; }
.partners { display: flex; flex-wrap: wrap; gap: 6px; }
.partner { display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 10px 0 4px; border-radius: 999px; border: 1px solid var(--line-strong); background: var(--surface-2); color: var(--text); font: inherit; font-size: 13px; cursor: pointer; }
.partner.active { border-color: var(--accent); background: var(--accent-soft); }
.unread { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 999px; background: var(--accent); color: var(--accent-ink); font-size: 10.5px; font-weight: 700; display: inline-grid; place-items: center; }
</style>
