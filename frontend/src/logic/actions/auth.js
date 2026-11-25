// Сценарии аутентификации: глаголы пользователя.
// Регистрирует провайдеры транспорта при bootstrap (см. main.js).
import {
  postLogin,
  postAdminKey,
  postRefresh,
  postLogout,
  postRegister,
  getMe,
  registerTokenProvider,
  registerRefreshHandler,
  registerUnauthorizedHandler,
} from '../api/index.js'
import { useAuthStore } from '../store/index.js'
import { registerOffsetProvider } from '../utils/tz.js'
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
import { resetChat } from './chat.js'

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
  resetChat()
  clearScheduleCaches()
  invalidateStatisticsLoads()
  clearStatisticsFilters()
  invalidateAllLoads()
}

export function registerAuthProviders({ onUnauthorized }) {
  registerTokenProvider(() => useAuthStore().accessToken)
  registerOffsetProvider(() => useAuthStore().user?.timezone_offset ?? 0)
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
  // Профиль с личным поясом: без него время до перезагрузки показывалось бы в UTC.
  try {
    useAuthStore().setUser(await getMe())
  } catch {
    // Профиль догрузится при следующем восстановлении сессии; вход не срываем.
  }
  return data
}

export async function registerUser({ role, username, password, fullName, email }) {
  // Регистрация сразу создаёт сессию: бэк возвращает токены, повторный логин не нужен.
  // Личный пояс по умолчанию — пояс браузера; потом меняется в настройках.
  const timezoneOffset = Math.max(-12, Math.min(14, Math.round(-new Date().getTimezoneOffset() / 60)))
  const data = await postRegister({ role, username, password, fullName, email, timezoneOffset })
  persistSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: { user_id: data.user_id, role: data.role, timezone_offset: timezoneOffset },
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

// Вход владельца по уникальному ключу: та же сессия, что у обычного входа, роль admin.
export async function loginAdminWithKey(key) {
  const data = await postAdminKey({ key: key.trim() })
  // Вход поверх чужой сессии в этой вкладке: данные прежнего пользователя не оставляем.
  if (useAuthStore().user) resetDomainState()
  persistSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: { user_id: data.user_id, role: data.role },
  })
  try {
    useAuthStore().setUser(await getMe())
  } catch {
    // Профиль догрузится при восстановлении сессии.
  }
  return data
}
