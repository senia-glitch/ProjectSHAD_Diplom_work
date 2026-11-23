// Сценарии аутентификации: глаголы пользователя.
// Регистрирует провайдеры транспорта при bootstrap (см. main.js).
import {
  postLogin,
  postRefresh,
  postLogout,
  postRegister,
  getMe,
  registerTokenProvider,
  registerRefreshHandler,
  registerUnauthorizedHandler,
} from '../api/index.js'
import { useAuthStore } from '../store/index.js'
import {
  useProfileStore,
  useScheduleStore,
  useBookingsStore,
  useRosterStore,
  useStatisticsStore,
  useAdminStore,
  useNotificationsStore,
} from '../store/index.js'
import { clearScheduleCaches } from './schedule.js'
import { invalidateStatisticsLoads, clearStatisticsFilters } from './statistics.js'
import { invalidateAllLoads } from './loading.js'

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

function readPersisted() {
  return {
    accessToken: sessionStorage.getItem(ACCESS_KEY),
    refreshToken: sessionStorage.getItem(REFRESH_KEY),
  }
}

function persistSession({ accessToken, refreshToken, user }) {
  const store = useAuthStore()
  store.setSession({ accessToken, refreshToken, user: user ?? store.user })
  if (accessToken) sessionStorage.setItem(ACCESS_KEY, accessToken)
  if (refreshToken) sessionStorage.setItem(REFRESH_KEY, refreshToken)
}

function clearPersistedSession() {
  useAuthStore().clearSession()
  sessionStorage.removeItem(ACCESS_KEY)
  sessionStorage.removeItem(REFRESH_KEY)
  resetDomainState()
}

// Сброс доменных данных при выходе: PII предыдущего пользователя не должны
// оставаться в памяти (store) и модульных кэшах при входе следующего.
function resetDomainState() {
  useProfileStore().$reset()
  useScheduleStore().$reset()
  useBookingsStore().$reset()
  useRosterStore().$reset()
  useStatisticsStore().$reset()
  useAdminStore().$reset()
  useNotificationsStore().$reset()
  clearScheduleCaches()
  invalidateStatisticsLoads()
  clearStatisticsFilters()
  invalidateAllLoads()
}

export function registerAuthProviders({ onUnauthorized }) {
  registerTokenProvider(() => useAuthStore().accessToken)
  registerRefreshHandler(() => refreshSession())
  registerUnauthorizedHandler(async () => {
    clearPersistedSession()
    if (onUnauthorized) await onUnauthorized()
  })
}

export async function loginUser({ username, password }) {
  const data = await postLogin({ username, password })
  persistSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: { user_id: data.user_id, role: data.role },
  })
  return data
}

export async function registerUser({ role, username, password, fullName, email }) {
  // Регистрация сразу создаёт сессию: бэк возвращает токены, повторный логин не нужен.
  const data = await postRegister({ role, username, password, fullName, email })
  persistSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: { user_id: data.user_id, role: data.role },
  })
  return data
}

export async function refreshSession() {
  const store = useAuthStore()
  const refreshToken = store.refreshToken || readPersisted().refreshToken
  if (!refreshToken) return null
  try {
    const data = await postRefresh({ refreshToken })
    persistSession({ accessToken: data.access_token, refreshToken: data.refresh_token })
    return data.access_token
  } catch {
    // Провал refresh — очистка без сетевого запроса (§6.5).
    clearPersistedSession()
    return null
  }
}

export async function restoreSession() {
  const store = useAuthStore()
  if (store.user) return true
  const { accessToken, refreshToken } = readPersisted()
  if (!accessToken) return false
  store.setSession({ accessToken, refreshToken, user: null })
  try {
    store.setUser(await getMe())
    return true
  } catch {
    // Неудачное восстановление: не оставляем «полу-сессию»
    // (токен в store при user === null).
    clearPersistedSession()
    return false
  }
}

export async function logoutUser() {
  const store = useAuthStore()
  const refreshToken = store.refreshToken || readPersisted().refreshToken
  if (refreshToken) {
    try {
      await postLogout({ refreshToken })
    } catch {
      // Best-effort: локальный выход в любом случае.
    }
  }
  clearPersistedSession()
}
