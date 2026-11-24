<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div ref="root" class="pp testing-host" @click="onLinkClick">
      <div v-if="loading" class="skeleton tall" aria-hidden="true"></div>
      <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    </div>
  </MainLayout>
</template>

<script setup>
// Хост перенесённых DOM-страниц тестирования (ui/legacy/testing).
// Страница выбирается по маршруту и роли; навигация внутри модуля идёт через vue-router.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { requestTesting } from '../../../logic/actions/index.js'
import { askConfirm, configureTesting, leaveMessage, resetLeaveGuard, testingPages } from '../../legacy/testing/kit.js'

const PAGES = {
  'testing-home': { tutor: 'teacherTests', student: 'available' },
  'testing-new': { tutor: 'testEditor' },
  'testing-edit': { tutor: 'testEditor' },
  'testing-test': { tutor: 'testOverview' },
  'testing-take': { student: 'take' },
  'testing-results': { student: 'myResults' },
  'testing-result': { tutor: 'teacherResult', student: 'myResult' },
}
const TITLES = { tutor: 'Тесты', student: 'Тесты' }

const route = useRoute()
const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const root = ref(null)
const loading = ref(false)
const error = ref('')
let token = 0
let skipGuard = false

async function render(target = route) {
  const name = PAGES[target.name]?.[role.value]
  const current = ++token
  resetLeaveGuard()
  error.value = ''
  if (!name) {
    error.value = 'Страница недоступна для вашей роли'
    return
  }
  const timer = setTimeout(() => { if (current === token) loading.value = true }, 300)
  try {
    const node = await testingPages[name](...(target.params.id ? [target.params.id] : []))
    if (current !== token || !root.value) return
    root.value.querySelector(':scope > .testing-page')?.remove()
    node.classList.add('testing-page')
    root.value.append(node)
    window.scrollTo(0, 0)
    document.title = `${root.value.querySelector('h1')?.textContent || TITLES[role.value]} · SHAD`
  } catch (e) {
    if (current !== token) return
    root.value?.querySelector(':scope > .testing-page')?.remove()
    error.value = e?.message || 'Ошибка загрузки'
  } finally {
    clearTimeout(timer)
    if (current === token) loading.value = false
  }
}

function onLinkClick(event) {
  const link = event.target.closest('a[href]')
  if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return
  const href = link.getAttribute('href')
  if (!href.startsWith('/')) return
  event.preventDefault()
  router.push(href)
}

async function confirmLeave() {
  const message = leaveMessage()
  if (!message || skipGuard) { skipGuard = false; return true }
  return askConfirm('Уйти со страницы?', message, { okText: 'Уйти', danger: true, cancelText: 'Остаться' })
}

function beforeUnload(event) {
  if (leaveMessage()) { event.preventDefault(); event.returnValue = '' }
}

configureTesting({
  request: (path, opts) => requestTesting(path, opts),
  navigate: (path) => { skipGuard = true; router.push(path) },
  rerender: () => render(),
})

// Все маршруты модуля используют этот компонент: Vue переиспользует экземпляр,
// поэтому страница перерисовывается по смене адреса, а защита ухода — в обоих хуках.
onBeforeRouteUpdate(() => confirmLeave())
onBeforeRouteLeave(() => confirmLeave())
watch(() => route.fullPath, () => { if (String(route.name).startsWith('testing-')) render() })
watch(role, () => render())
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); render() })
onBeforeUnmount(() => { window.removeEventListener('beforeunload', beforeUnload); resetLeaveGuard() })
</script>

<style scoped>
.testing-host { min-height: 240px; }
</style>
