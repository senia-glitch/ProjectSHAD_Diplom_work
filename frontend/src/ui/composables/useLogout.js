// Общий сценарий выхода: используется десятью страницами,
// поэтому живёт в composables, а не копипастится.
import { logoutUser } from '../../logic/actions/index.js'

export function useLogout() {
  async function handleLogout() {
    await logoutUser()
    window.location.href = '/login'
  }
  return { handleLogout }
}
