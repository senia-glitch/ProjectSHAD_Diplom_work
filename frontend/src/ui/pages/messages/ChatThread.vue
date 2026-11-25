<template>
  <div class="pp thread" :class="{ compact }">
    <div ref="listRef" class="thread-list" role="log" aria-live="polite" aria-relevant="additions" tabindex="0">
      <button v-if="thread.hasMore" type="button" class="more older" :disabled="loadingOlder" @click="loadOlder">
        {{ loadingOlder ? 'Загрузка…' : 'Показать раньше' }}
      </button>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p v-else-if="thread.loaded && !thread.items.length" class="muted empty">Сообщений пока нет — напишите первым.</p>
      <template v-for="(m, i) in thread.items" :key="m.id">
        <div v-if="i === 0 || day(m) !== day(thread.items[i - 1])" class="day">{{ dayLabel(m) }}</div>
        <div class="chat-msg" :class="{ mine: m.sender_id === me }">
          <div class="bubble">
            <p class="text">{{ m.text }}</p>
            <span class="time">{{ time(m) }}<template v-if="m.sender_id === me"> · {{ m.read_at ? 'прочитано' : 'отправлено' }}</template></span>
          </div>
        </div>
      </template>
    </div>
    <form v-if="canWrite" class="thread-form" @submit.prevent="send">
      <textarea
        ref="inputRef"
        v-model="text"
        rows="1"
        maxlength="2000"
        :placeholder="`Сообщение для ${partnerName}… (Enter — отправить, Shift+Enter — новая строка)`"
        :aria-label="`Сообщение для ${partnerName}`"
        @keydown.enter.exact.prevent="send"
        @input="autosize"
      ></textarea>
      <button type="submit" class="btn primary" :disabled="sending || !text.trim()">Отправить</button>
    </form>
    <p v-else class="muted small locked">Связи с {{ partnerName }} больше нет — переписка доступна только для чтения.</p>
    <p v-if="sendError" class="error-text small" role="alert">{{ sendError }}</p>
  </div>
</template>

<script setup>
// Переписка с одним собеседником: история порциями, отправка, отметка «прочитано».
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { loadChatThread, markChatRead, onChatEvent, sendChatMessage, setOpenChat } from '../../../logic/actions/index.js'
import { useAuthStore, useChatStore } from '../../../logic/store/index.js'

const props = defineProps({
  partnerId: { type: Number, required: true },
  partnerName: { type: String, default: 'собеседника' },
  canWrite: { type: Boolean, default: true },
  compact: { type: Boolean, default: false },
})

const store = useChatStore()
const me = computed(() => useAuthStore().user?.user_id)
const thread = computed(() => store.thread(props.partnerId))
const listRef = ref(null)
const inputRef = ref(null)
const text = ref('')
const sending = ref(false)
const sendError = ref('')
const error = ref('')
const loadingOlder = ref(false)

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
const day = (m) => String(m.created_at).slice(0, 10)
const time = (m) => String(m.created_at).slice(11, 16)
function dayLabel(m) {
  const [y, mo, d] = day(m).split('-').map(Number)
  return `${d} ${MONTHS[mo - 1]} ${y}`
}

function scrollToEnd() {
  nextTick(() => { if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight })
}
function nearEnd() {
  const el = listRef.value
  return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 120
}
function autosize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

async function open() {
  error.value = ''
  setOpenChat(props.partnerId)
  try {
    if (!thread.value.loaded) await loadChatThread(props.partnerId)
    await markChatRead(props.partnerId)
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить переписку'
  }
  scrollToEnd()
}

async function loadOlder() {
  const el = listRef.value
  const before = el ? el.scrollHeight : 0
  loadingOlder.value = true
  try {
    await loadChatThread(props.partnerId, { older: true })
    await nextTick()
    if (el) el.scrollTop = el.scrollHeight - before // остаёмся на том же сообщении
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить сообщения'
  } finally {
    loadingOlder.value = false
  }
}

async function send() {
  const value = text.value.trim()
  if (!value || sending.value) return
  sending.value = true
  sendError.value = ''
  try {
    await sendChatMessage(props.partnerId, value)
    text.value = ''
    nextTick(autosize)
    scrollToEnd()
  } catch (e) {
    sendError.value = e.message || 'Не удалось отправить сообщение'
  } finally {
    sending.value = false
    nextTick(() => inputRef.value?.focus())
  }
}

// Новое сообщение в открытом диалоге: прокрутка вниз и отметка «прочитано».
const off = onChatEvent((msg) => {
  if (msg.t !== 'message') return
  const m = msg.message
  const involved = [m.tutor_user_id, m.student_user_id].includes(props.partnerId)
  if (!involved) return
  const stick = nearEnd() || m.sender_id === me.value
  if (m.sender_id === props.partnerId && !document.hidden) markChatRead(props.partnerId)
  if (stick) scrollToEnd()
})

watch(() => props.partnerId, open, { immediate: true })
onBeforeUnmount(() => {
  off()
  if (store.openPartner === props.partnerId) setOpenChat(null)
})
</script>

<style scoped>
.thread { display: flex; flex-direction: column; min-height: 0; height: 100%; }
.thread-list { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; padding: 12px 4px; }
.older { align-self: center; }
.empty { text-align: center; margin: auto; }
.day { align-self: center; font-size: 12px; color: var(--muted); margin: 8px 0 2px; }
.chat-msg { display: flex; }
.chat-msg.mine { justify-content: flex-end; }
.bubble { max-width: min(560px, 82%); padding: 8px 12px; border-radius: 14px 14px 14px 4px; background: var(--surface-2); }
.mine .bubble { border-radius: 14px 14px 4px 14px; background: var(--accent-soft); }
.text { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14.5px; }
.time { display: block; margin-top: 2px; font-size: 11px; color: var(--muted); text-align: right; }
.thread-form { display: flex; gap: 8px; align-items: flex-end; padding-top: 10px; border-top: 1px solid var(--line); }
.thread-form textarea { flex: 1; min-height: 40px; max-height: 160px; resize: none; }
.locked { padding-top: 10px; border-top: 1px solid var(--line); margin: 0; }
.compact .bubble { max-width: 92%; }
.compact .text { font-size: 13.5px; }
.compact .thread-form textarea { min-height: 36px; }
</style>
