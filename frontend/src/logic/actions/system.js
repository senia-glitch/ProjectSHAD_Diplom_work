// Сценарии страницы системной статистики (админ).
import { getSystemStats, getServerTime } from '../api/index.js'

export async function loadSystemStats() {
  return getSystemStats()
}

export async function loadServerTime() {
  return getServerTime()
}
