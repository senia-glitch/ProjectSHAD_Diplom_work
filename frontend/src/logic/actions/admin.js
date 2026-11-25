// Сценарии страницы управления.
import { listAdminUsers, getAdminUser, patchAdminUser, deleteAdminUser, postBlockUser, postUnblockUser } from '../api/index.js'
import { useAdminStore } from '../store/index.js'

export async function loadAdminUsers({ limit = 100, offset = 0 } = {}) {
  const data = await listAdminUsers({ limit, offset })
  useAdminStore().setUsers(data.users || [])
}

export async function loadAdminUser(userId) {
  const data = await getAdminUser(userId)
  useAdminStore().setCurrentUser(data)
  return data
}

export async function saveAdminUser(userId, patch) {
  const updated = await patchAdminUser(userId, patch)
  useAdminStore().updateUserInList(userId, updated)
  return updated
}

// ----- Админ-панель владельца -----
export {
  fetchAdminDashboard as loadAdminDashboard,
  postRotateAdminKey as rotateAdminKey,
  fetchAdminAudit as loadAdminAudit,
  postResetPassword as resetUserPassword,
  fetchDbTables as loadDbTables,
  fetchDbRows as loadDbRows,
  patchDbRow as updateDbRow,
  deleteDbRow as removeDbRow,
  postDbSql as runDbSql,
} from '../api/index.js'

export async function removeAdminUser(userId) {
  const res = await deleteAdminUser(userId)
  const store = useAdminStore()
  store.setUsers(store.users.filter((u) => u.user_id !== userId))
  if (store.currentUser?.user_id === userId) store.setCurrentUser(null)
  return res
}

export async function blockUser(userId, reason) {
  const res = await postBlockUser(userId, reason)
  useAdminStore().updateUserInList(userId, { blocked_at: new Date().toISOString(), block_reason: reason || null })
  return res
}

export async function unblockUser(userId) {
  const res = await postUnblockUser(userId)
  useAdminStore().updateUserInList(userId, { blocked_at: null, block_reason: null })
  return res
}
