<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="pp key-login">
      <form class="form-card stack" novalidate @submit.prevent="handleSubmit">
        <div>
          <p class="eyebrow">Владелец платформы</p>
          <h1>Вход в админ-панель</h1>
          <p class="muted small">Вставьте ключ администратора. Ключ выдаётся командой на сервере и показывается один раз.</p>
        </div>
        <label>
          Ключ
          <input
            ref="keyInput"
            v-model="key"
            type="password"
            autocomplete="off"
            spellcheck="false"
            placeholder="shad_admin_…"
            :aria-invalid="!!error"
          />
        </label>
        <div v-if="error" class="notice error" role="alert">{{ error }}</div>
        <button type="submit" class="btn primary" :disabled="loading || !key.trim()">{{ loading ? 'Проверка…' : 'Войти' }}</button>
        <p class="muted small">После 5 неверных попыток вход с этого адреса закрывается на 15 минут.</p>
      </form>
    </div>
  </MainLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useLogout, useUser } from '../../composables/index.js'
import { loginAdminWithKey } from '../../../logic/actions/index.js'

const router = useRouter()
const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const key = ref('')
const error = ref('')
const loading = ref(false)
const keyInput = ref(null)

async function handleSubmit() {
  if (!key.value.trim()) return
  error.value = ''
  loading.value = true
  try {
    await loginAdminWithKey(key.value)
    key.value = ''
    router.push('/admin')
  } catch (e) {
    error.value = e.message || 'Не удалось войти'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  document.title = 'Админ-панель · SHAD'
  keyInput.value?.focus()
})
</script>

<style scoped>
.key-login { display: grid; place-items: center; min-height: 60vh; padding: 24px 0; }
.key-login .form-card { width: 100%; max-width: 440px; }
.key-login h1 { font-size: 26px; margin: 0 0 6px; }
.eyebrow { color: var(--accent); text-transform: uppercase; font-size: 10px; font-weight: 600; letter-spacing: .12em; margin: 0 0 12px; }
</style>
