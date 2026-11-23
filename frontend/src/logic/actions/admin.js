// Сценарии страницы управления.
import { listAdminUsers, getAdminUser, patchAdminUser } from '../api/index.js'
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
